import re
import uuid
from datetime import datetime

from app.extensions import db


def _uuid() -> str:
    return str(uuid.uuid4())


class Template(db.Model):
    __tablename__ = "review_templates"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(255), nullable=False)
    doc_type = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    documents = db.relationship("Document", backref="template")

    @property
    def variables(self) -> list[str]:
        return sorted(set(re.findall(r"{{\s*([a-zA-Z0-9_]+)\s*}}", self.content)))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "doc_type": self.doc_type,
            "content": self.content,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
        }


class Document(db.Model):
    __tablename__ = "review_documents"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    doc_type = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(100), default="automation")
    status = db.Column(db.String(10), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewer_notes = db.Column(db.Text, nullable=True)
    risk_level = db.Column(db.String(10), default="low")
    template_id = db.Column(db.String(36), db.ForeignKey("review_templates.id"), nullable=True)
    public_token = db.Column(db.String(64), unique=True, default=_uuid)

    risk_flags = db.relationship("RiskFlag", backref="document", cascade="all, delete-orphan")
    audit_log = db.relationship("AuditEntry", backref="document", cascade="all, delete-orphan",
                                 order_by="AuditEntry.timestamp")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "doc_type": self.doc_type,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reviewer_notes": self.reviewer_notes,
            "risk_level": self.risk_level,
            "risk_flags": [f.to_dict() for f in self.risk_flags],
            "audit_log": [a.to_dict() for a in self.audit_log],
            "template_id": self.template_id,
            "public_token": self.public_token,
        }


class RiskFlag(db.Model):
    __tablename__ = "review_risk_flags"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey("review_documents.id"), nullable=False)
    field = db.Column(db.String(100), nullable=True)
    issue = db.Column(db.String(500), nullable=False)
    severity = db.Column(db.String(10), nullable=False)

    def to_dict(self):
        return {"field": self.field, "issue": self.issue, "severity": self.severity}


class AuditEntry(db.Model):
    __tablename__ = "review_audit_entries"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String(36), db.ForeignKey("review_documents.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    actor = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "actor": self.actor,
            "action": self.action,
            "detail": self.detail,
        }
