from flask import request, jsonify, abort

from app.review_queue import review_queue_bp
from app.review_queue.models import db, Document, RiskFlag, AuditEntry, Template
from app.review_queue.risk import assess_risk

RISK_ORDER = {"high": 0, "medium": 1, "low": 2}


def _reviewer_name(fallback: str = "reviewer") -> str:
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return getattr(current_user, "username", None) or getattr(current_user, "email", fallback)
    except ImportError:
        pass
    return (request.get_json(silent=True) or {}).get("reviewer") or fallback


def _create_document(*, title, content, doc_type, source, extracted_fields=None,
                      extraction_confidence=None, template_id=None) -> Document:
    extracted_fields = extracted_fields or {}
    extraction_confidence = extraction_confidence or {}
    level, flags = assess_risk(doc_type, content, extracted_fields, extraction_confidence)

    doc = Document(title=title, content=content, doc_type=doc_type, source=source,
                   risk_level=level, template_id=template_id)
    db.session.add(doc)
    db.session.flush()

    for f in flags:
        db.session.add(RiskFlag(document_id=doc.id, field=f.get("field"), issue=f["issue"], severity=f["severity"]))
    db.session.add(AuditEntry(document_id=doc.id, actor=source, action="created",
                              detail=f"Risk assessed as {level}"))
    db.session.commit()
    return doc


def _log(doc: Document, actor: str, action: str, detail: str | None = None):
    db.session.add(AuditEntry(document_id=doc.id, actor=actor, action=action, detail=detail))
    db.session.commit()


@review_queue_bp.route("/queue", methods=["GET", "POST"])
def queue_list_create():
    if request.method == "POST":
        payload = request.get_json(force=True)
        for required in ("title", "content", "doc_type"):
            if not payload.get(required):
                return jsonify({"detail": f"'{required}' is required"}), 400

        doc = _create_document(
            title=payload["title"],
            content=payload["content"],
            doc_type=payload["doc_type"],
            source=payload.get("source", "automation"),
            extracted_fields=payload.get("extracted_fields", {}),
            extraction_confidence=payload.get("extraction_confidence", {}),
        )
        return jsonify(doc.to_dict()), 201

    doc_status = request.args.get("status", "pending")
    sort = request.args.get("sort", "risk")

    query = Document.query
    if doc_status != "all":
        query = query.filter_by(status=doc_status)

    docs = query.all()
    if sort == "risk":
        docs.sort(key=lambda d: (RISK_ORDER[d.risk_level], d.created_at))
    else:
        docs.sort(key=lambda d: d.created_at)

    return jsonify([d.to_dict() for d in docs])


@review_queue_bp.route("/queue/<doc_id>", methods=["GET", "PATCH"])
def queue_detail(doc_id):
    doc = Document.query.get(doc_id) or abort(404)

    if request.method == "GET":
        return jsonify(doc.to_dict())

    if doc.status != "pending":
        return jsonify({"detail": "Only pending documents can be edited"}), 400

    payload = request.get_json(force=True)
    changed = []
    if "title" in payload and payload["title"] != doc.title:
        doc.title = payload["title"]
        changed.append("title")
    if "content" in payload and payload["content"] != doc.content:
        doc.content = payload["content"]
        changed.append("content")

    if changed:
        db.session.commit()
        _log(doc, _reviewer_name(payload.get("editor", "reviewer")), "edited", f"Changed: {', '.join(changed)}")
    return jsonify(doc.to_dict())


@review_queue_bp.route("/queue/<doc_id>/approve", methods=["POST"])
def queue_approve(doc_id):
    doc = Document.query.get(doc_id) or abort(404)
    if doc.status != "pending":
        return jsonify({"detail": "Document already reviewed"}), 400

    payload = request.get_json(silent=True) or {}
    doc.status = "approved"
    doc.reviewer_notes = payload.get("notes")
    db.session.commit()
    _log(doc, _reviewer_name(), "approved", doc.reviewer_notes)
    return jsonify(doc.to_dict())


@review_queue_bp.route("/queue/<doc_id>/reject", methods=["POST"])
def queue_reject(doc_id):
    doc = Document.query.get(doc_id) or abort(404)
    if doc.status != "pending":
        return jsonify({"detail": "Document already reviewed"}), 400

    payload = request.get_json(silent=True) or {}
    doc.status = "rejected"
    doc.reviewer_notes = payload.get("notes")
    db.session.commit()
    _log(doc, _reviewer_name(), "rejected", doc.reviewer_notes)
    return jsonify(doc.to_dict())


@review_queue_bp.route("/queue/bulk-approve", methods=["POST"])
def queue_bulk_approve():
    payload = request.get_json(force=True)
    document_ids = payload.get("document_ids", [])
    max_risk = payload.get("max_risk", "low")
    notes = payload.get("notes")
    reviewer = _reviewer_name(payload.get("reviewer", "reviewer"))

    processed, skipped = [], []
    for doc_id in document_ids:
        doc = Document.query.get(doc_id)
        if not doc:
            skipped.append({"id": doc_id, "reason": "not found"})
            continue
        if doc.status != "pending":
            skipped.append({"id": doc_id, "reason": "already reviewed"})
            continue
        if RISK_ORDER[doc.risk_level] > RISK_ORDER[max_risk]:
            skipped.append({"id": doc_id, "reason": f"risk level {doc.risk_level} exceeds max {max_risk}"})
            continue
        doc.status = "approved"
        doc.reviewer_notes = notes
        db.session.commit()
        _log(doc, reviewer, "approved", f"Bulk approval. {notes or ''}".strip())
        processed.append(doc_id)

    return jsonify({"processed": processed, "skipped": skipped})


@review_queue_bp.route("/templates", methods=["GET", "POST"])
def template_list_create():
    if request.method == "POST":
        payload = request.get_json(force=True)
        for required in ("name", "doc_type", "content"):
            if not payload.get(required):
                return jsonify({"detail": f"'{required}' is required"}), 400
        template = Template(name=payload["name"], doc_type=payload["doc_type"], content=payload["content"])
        db.session.add(template)
        db.session.commit()
        return jsonify(template.to_dict()), 201

    templates = Template.query.order_by(Template.name).all()
    return jsonify([t.to_dict() for t in templates])


@review_queue_bp.route("/templates/<template_id>", methods=["GET", "DELETE"])
def template_detail(template_id):
    template = Template.query.get(template_id) or abort(404)
    if request.method == "DELETE":
        db.session.delete(template)
        db.session.commit()
        return "", 204
    return jsonify(template.to_dict())


@review_queue_bp.route("/templates/<template_id>/generate", methods=["POST"])
def template_generate(template_id):
    template = Template.query.get(template_id) or abort(404)
    payload = request.get_json(force=True)
    values = payload.get("values", {})
    confidence = payload.get("confidence", {})

    content = template.content
    for var, value in values.items():
        content = content.replace(f"{{{{{var}}}}}", value)

    missing = [v for v in template.variables if v not in values]
    doc = _create_document(
        title=payload.get("title") or template.name,
        content=content,
        doc_type=template.doc_type,
        source=payload.get("source", "template"),
        extracted_fields=values,
        extraction_confidence=confidence,
        template_id=template.id,
    )
    if missing:
        db.session.add(RiskFlag(document_id=doc.id, issue=f"Template variables left unfilled: {', '.join(missing)}",
                                 severity="high"))
        doc.risk_level = "high"
        db.session.commit()

    return jsonify(doc.to_dict())
