"""Authentication models for JWT-based access control."""

import uuid
from datetime import datetime
from enum import Enum

from app.extensions import db
from app.security import hash_password, check_password


class UserRole(str, Enum):
    """User roles for role-based access control."""

    ADMIN = "admin"
    REVIEWER = "reviewer"
    AUTOMATION = "automation"


def _uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class User(db.Model):
    """User model with authentication and role management."""

    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    roles = db.Column(db.String(100), default=UserRole.REVIEWER.value, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login = db.Column(db.DateTime, nullable=True)

    audit_entries = db.relationship(
        "AuditEntry", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str):
        """Set and hash the user's password."""
        self.password_hash = hash_password(password)

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return check_password(self.password_hash, password)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles.split(",")

    def add_role(self, role: str):
        """Add a role to the user."""
        if not self.has_role(role):
            roles = self.roles.split(",") if self.roles else []
            roles.append(role)
            self.roles = ",".join(sorted(set(roles)))

    def remove_role(self, role: str):
        """Remove a role from the user."""
        if self.has_role(role):
            roles = self.roles.split(",")
            roles.remove(role)
            self.roles = ",".join(roles) if roles else UserRole.REVIEWER.value

    def get_roles_list(self) -> list:
        """Get user roles as a list."""
        return [r.strip() for r in self.roles.split(",") if r.strip()]

    def to_dict(self, include_sensitive: bool = False):
        """Convert user to dictionary."""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "roles": self.get_roles_list(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
        if include_sensitive:
            data["password_hash"] = self.password_hash
        return data
