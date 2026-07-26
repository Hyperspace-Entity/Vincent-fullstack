"""Security-hardened review queue routes with input validation and error handling."""

import logging
from datetime import datetime

from flask import request, jsonify, abort
from pydantic import ValidationError

from app.review_queue import review_queue_bp
from app.review_queue.models import db, Document, RiskFlag, AuditEntry, Template
from app.review_queue.risk import assess_risk
from app.extensions import limiter
from app.schemas import (
    DocumentCreateRequest,
    DocumentUpdateRequest,
    DocumentApprovalRequest,
    BulkApprovalRequest,
    TemplateCreateRequest,
    TemplateGenerateRequest,
)
from app.security import (
    require_auth,
    require_role,
    sanitize_string,
    sanitize_dict,
    log_security_event,
)

logger = logging.getLogger(__name__)
RISK_ORDER = {"high": 0, "medium": 1, "low": 2}
ALLOWED_DOC_TYPES = {"invoice", "contract", "form", "report", "other"}
ALLOWED_STATUSES = {"pending", "approved", "rejected"}


def _reviewer_name(fallback: str = "system") -> str:
    """Get reviewer name from request context."""
    try:
        return getattr(request, "user_id", fallback) or fallback
    except Exception:
        return fallback


def _create_document(
    *,
    title: str,
    content: str,
    doc_type: str,
    source: str,
    extracted_fields: dict = None,
    extraction_confidence: dict = None,
    template_id: str = None,
) -> Document:
    """Create a new document with risk assessment."""
    extracted_fields = extracted_fields or {}
    extraction_confidence = extraction_confidence or {}

    level, flags = assess_risk(doc_type, content, extracted_fields, extraction_confidence)

    doc = Document(
        title=sanitize_string(title),
        content=sanitize_string(content),
        doc_type=doc_type,
        source=source,
        risk_level=level,
        template_id=template_id,
    )
    db.session.add(doc)
    db.session.flush()

    for f in flags:
        db.session.add(
            RiskFlag(
                document_id=doc.id,
                field=f.get("field"),
                issue=f["issue"],
                severity=f["severity"],
            )
        )

    db.session.add(
        AuditEntry(
            document_id=doc.id,
            actor=source,
            action="created",
            detail=f"Risk assessed as {level}",
        )
    )
    db.session.commit()
    return doc


def _log(doc: Document, actor: str, action: str, detail: str = None):
    """Log an audit entry for a document action."""
    db.session.add(
        AuditEntry(document_id=doc.id, actor=actor, action=action, detail=detail)
    )
    db.session.commit()


@review_queue_bp.route("/queue", methods=["GET", "POST"])
@require_auth
@limiter.limit("100/hour")
def queue_list_create():
    """Get or create documents in the review queue."""
    if request.method == "POST":
        try:
            payload = request.get_json(force=True)
            doc_data = DocumentCreateRequest(**payload)
        except ValidationError as e:
            logger.warning(f"Invalid document creation request: {e}")
            return jsonify({"detail": "Invalid request data", "errors": e.errors()}), 400

        try:
            doc = _create_document(
                title=doc_data.title,
                content=doc_data.content,
                doc_type=doc_data.doc_type,
                source=doc_data.source,
                extracted_fields=sanitize_dict(doc_data.extracted_fields or {}),
                extraction_confidence=doc_data.extraction_confidence or {},
            )
            log_security_event(
                "document_created",
                user_id=_reviewer_name(),
                action="create_document",
                details=f"Document {doc.id} created",
            )
            return jsonify(doc.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Document creation error: {str(e)}")
            return jsonify({"detail": "Failed to create document"}), 500

    # GET: List documents
    try:
        doc_status = request.args.get("status", "pending")
        sort = request.args.get("sort", "risk")
        skip = int(request.args.get("skip", 0))
        limit = min(int(request.args.get("limit", 50)), 100)  # Cap at 100

        if doc_status not in ALLOWED_STATUSES and doc_status != "all":
            return jsonify({"detail": "Invalid status filter"}), 400

        query = Document.query
        if doc_status != "all":
            query = query.filter_by(status=doc_status)

        docs = query.offset(skip).limit(limit).all()

        if sort == "risk":
            docs.sort(key=lambda d: (RISK_ORDER.get(d.risk_level, 2), d.created_at))
        elif sort == "date":
            docs.sort(key=lambda d: d.created_at, reverse=True)
        else:
            return jsonify({"detail": "Invalid sort parameter"}), 400

        return jsonify([d.to_dict() for d in docs]), 200
    except ValueError as e:
        logger.warning(f"Invalid query parameters: {str(e)}")
        return jsonify({"detail": "Invalid query parameters"}), 400
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        return jsonify({"detail": "Failed to fetch documents"}), 500


@review_queue_bp.route("/queue/<doc_id>", methods=["GET", "PATCH"])
@require_auth
@limiter.limit("100/hour")
def queue_detail(doc_id):
    """Get or update a specific document."""
    if not isinstance(doc_id, str) or len(doc_id) > 36:
        return jsonify({"detail": "Invalid document ID"}), 400

    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"detail": "Document not found"}), 404

    if request.method == "GET":
        return jsonify(doc.to_dict()), 200

    # PATCH: Update document
    if doc.status != "pending":
        return jsonify({"detail": "Only pending documents can be edited"}), 400

    try:
        payload = request.get_json(force=True)
        update_data = DocumentUpdateRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Invalid document update: {e}")
        return jsonify({"detail": "Invalid request data"}), 400

    changed = []
    if update_data.title and update_data.title != doc.title:
        doc.title = sanitize_string(update_data.title)
        changed.append("title")
    if update_data.content and update_data.content != doc.content:
        doc.content = sanitize_string(update_data.content)
        changed.append("content")

    if changed:
        db.session.commit()
        editor = update_data.editor or _reviewer_name()
        _log(doc, editor, "edited", f"Changed: {', '.join(changed)}")
        log_security_event(
            "document_edited",
            user_id=editor,
            action="edit_document",
            details=f"Document {doc_id} edited: {', '.join(changed)}",
        )

    return jsonify(doc.to_dict()), 200


@review_queue_bp.route("/queue/<doc_id>/approve", methods=["POST"])
@require_auth
@require_role("reviewer", "admin")
@limiter.limit("50/hour")
def queue_approve(doc_id):
    """Approve a document."""
    if not isinstance(doc_id, str) or len(doc_id) > 36:
        return jsonify({"detail": "Invalid document ID"}), 400

    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"detail": "Document not found"}), 404

    if doc.status != "pending":
        return jsonify({"detail": "Document already reviewed"}), 400

    try:
        payload = request.get_json(silent=True) or {}
        approval_data = DocumentApprovalRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Invalid approval request: {e}")
        return jsonify({"detail": "Invalid request data"}), 400

    try:
        doc.status = "approved"
        doc.reviewer_notes = sanitize_string(
            approval_data.notes or ""
        )
        db.session.commit()

        reviewer = approval_data.reviewer or _reviewer_name()
        _log(doc, reviewer, "approved", doc.reviewer_notes)

        log_security_event(
            "document_approved",
            user_id=reviewer,
            action="approve_document",
            details=f"Document {doc_id} approved",
        )

        return jsonify(doc.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Approval error: {str(e)}")
        return jsonify({"detail": "Failed to approve document"}), 500


@review_queue_bp.route("/queue/<doc_id>/reject", methods=["POST"])
@require_auth
@require_role("reviewer", "admin")
@limiter.limit("50/hour")
def queue_reject(doc_id):
    """Reject a document."""
    if not isinstance(doc_id, str) or len(doc_id) > 36:
        return jsonify({"detail": "Invalid document ID"}), 400

    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"detail": "Document not found"}), 404

    if doc.status != "pending":
        return jsonify({"detail": "Document already reviewed"}), 400

    try:
        payload = request.get_json(silent=True) or {}
        rejection_data = DocumentApprovalRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Invalid rejection request: {e}")
        return jsonify({"detail": "Invalid request data"}), 400

    try:
        doc.status = "rejected"
        doc.reviewer_notes = sanitize_string(
            rejection_data.notes or ""
        )
        db.session.commit()

        reviewer = rejection_data.reviewer or _reviewer_name()
        _log(doc, reviewer, "rejected", doc.reviewer_notes)

        log_security_event(
            "document_rejected",
            user_id=reviewer,
            action="reject_document",
            details=f"Document {doc_id} rejected",
        )

        return jsonify(doc.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Rejection error: {str(e)}")
        return jsonify({"detail": "Failed to reject document"}), 500


@review_queue_bp.route("/queue/bulk-approve", methods=["POST"])
@require_auth
@require_role("reviewer", "admin")
@limiter.limit("20/hour")  # Stricter rate limit for bulk operations
def queue_bulk_approve():
    """Approve multiple documents in bulk."""
    try:
        payload = request.get_json(force=True)
        bulk_data = BulkApprovalRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Invalid bulk approval request: {e}")
        return jsonify({"detail": "Invalid request data", "errors": e.errors()}), 400

    try:
        processed, skipped = [], []

        for doc_id in bulk_data.document_ids:
            if not isinstance(doc_id, str) or len(doc_id) > 36:
                skipped.append({"id": doc_id, "reason": "invalid format"})
                continue

            doc = Document.query.get(doc_id)
            if not doc:
                skipped.append({"id": doc_id, "reason": "not found"})
                continue
            if doc.status != "pending":
                skipped.append({"id": doc_id, "reason": "already reviewed"})
                continue
            if RISK_ORDER.get(doc.risk_level, 2) > RISK_ORDER.get(bulk_data.max_risk, 2):
                skipped.append(
                    {
                        "id": doc_id,
                        "reason": f"risk level {doc.risk_level} exceeds max {bulk_data.max_risk}",
                    }
                )
                continue

            doc.status = "approved"
            doc.reviewer_notes = sanitize_string(bulk_data.notes or "")
            db.session.commit()
            _log(
                doc,
                bulk_data.reviewer or _reviewer_name(),
                "approved",
                f"Bulk approval. {bulk_data.notes or ''}".strip(),
            )
            processed.append(doc_id)

        log_security_event(
            "bulk_approval",
            user_id=_reviewer_name(),
            action="bulk_approve",
            details=f"Bulk approved {len(processed)} documents, skipped {len(skipped)}",
        )

        return (
            jsonify({"processed": processed, "skipped": skipped, "count": len(processed)}),
            200,
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk approval error: {str(e)}")
        return jsonify({"detail": "Bulk approval failed"}), 500


@review_queue_bp.route("/templates", methods=["GET", "POST"])
@require_auth
@limiter.limit("50/hour")
def template_list_create():
    """Get or create document templates."""
    if request.method == "POST":
        try:
            payload = request.get_json(force=True)
            template_data = TemplateCreateRequest(**payload)
        except ValidationError as e:
            logger.warning(f"Invalid template creation request: {e}")
            return jsonify({"detail": "Invalid request data", "errors": e.errors()}), 400

        try:
            template = Template(
                name=sanitize_string(template_data.name),
                doc_type=template_data.doc_type,
                content=sanitize_string(template_data.content),
                created_by=_reviewer_name(),
            )
            db.session.add(template)
            db.session.commit()

            log_security_event(
                "template_created",
                user_id=_reviewer_name(),
                action="create_template",
                details=f"Template {template.id} created",
            )

            return jsonify(template.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Template creation error: {str(e)}")
            return jsonify({"detail": "Failed to create template"}), 500

    # GET: List templates
    try:
        templates = Template.query.order_by(Template.name).all()
        return jsonify([t.to_dict() for t in templates]), 200
    except Exception as e:
        logger.error(f"Error fetching templates: {str(e)}")
        return jsonify({"detail": "Failed to fetch templates"}), 500


@review_queue_bp.route("/templates/<template_id>", methods=["GET", "DELETE"])
@require_auth
@limiter.limit("50/hour")
def template_detail(template_id):
    """Get or delete a template."""
    if not isinstance(template_id, str) or len(template_id) > 36:
        return jsonify({"detail": "Invalid template ID"}), 400

    template = Template.query.get(template_id)
    if not template:
        return jsonify({"detail": "Template not found"}), 404

    if request.method == "DELETE":
        try:
            db.session.delete(template)
            db.session.commit()
            log_security_event(
                "template_deleted",
                user_id=_reviewer_name(),
                action="delete_template",
                details=f"Template {template_id} deleted",
            )
            return "", 204
        except Exception as e:
            db.session.rollback()
            logger.error(f"Template deletion error: {str(e)}")
            return jsonify({"detail": "Failed to delete template"}), 500

    return jsonify(template.to_dict()), 200


@review_queue_bp.route("/templates/<template_id>/generate", methods=["POST"])
@require_auth
@limiter.limit("50/hour")
def template_generate(template_id):
    """Generate a document from a template."""
    if not isinstance(template_id, str) or len(template_id) > 36:
        return jsonify({"detail": "Invalid template ID"}), 400

    template = Template.query.get(template_id)
    if not template:
        return jsonify({"detail": "Template not found"}), 404

    try:
        payload = request.get_json(force=True)
        generate_data = TemplateGenerateRequest(**payload)
    except ValidationError as e:
        logger.warning(f"Invalid template generation request: {e}")
        return jsonify({"detail": "Invalid request data"}), 400

    try:
        content = template.content
        sanitized_values = sanitize_dict(generate_data.values)

        for var, value in sanitized_values.items():
            content = content.replace(f"{{{{{var}}}}}", str(value))

        missing = [v for v in template.variables if v not in sanitized_values]

        doc = _create_document(
            title=generate_data.title or template.name,
            content=content,
            doc_type=template.doc_type,
            source=generate_data.source,
            extracted_fields=sanitized_values,
            extraction_confidence=generate_data.confidence or {},
            template_id=template.id,
        )

        if missing:
            db.session.add(
                RiskFlag(
                    document_id=doc.id,
                    issue=f"Template variables left unfilled: {', '.join(missing)}",
                    severity="high",
                )
            )
            doc.risk_level = "high"
            db.session.commit()

        log_security_event(
            "template_generated",
            user_id=_reviewer_name(),
            action="generate_document",
            details=f"Document {doc.id} generated from template {template_id}",
        )

        return jsonify(doc.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Template generation error: {str(e)}")
        return jsonify({"detail": "Failed to generate document"}), 500
