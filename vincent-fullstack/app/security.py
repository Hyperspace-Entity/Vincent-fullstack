"""Security utilities and helpers for the application."""

import logging
from functools import wraps
from datetime import datetime, timedelta

import jwt
from flask import current_app, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from html import escape

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a password using werkzeug security."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def check_password(password_hash: str, password: str) -> bool:
    """Check if a password matches its hash."""
    return check_password_hash(password_hash, password)


def generate_jwt_token(
    user_id: str,
    roles: list = None,
    expires_in: int = None,
    token_type: str = "access",
) -> str:
    """Generate a JWT token."""
    if expires_in is None:
        expires_in = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]

    payload = {
        "user_id": user_id,
        "roles": roles or [],
        "token_type": token_type,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
    }

    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    return token


def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Token expired")
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise ValueError("Invalid token")


def extract_token_from_request() -> str:
    """Extract JWT token from request headers."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:]


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize user input string."""
    if not isinstance(value, str):
        return str(value)
    # Escape HTML entities
    sanitized = escape(value)
    # Trim to max length
    return sanitized[:max_length]


def sanitize_dict(data: dict, max_length: int = 1000) -> dict:
    """Recursively sanitize dictionary values."""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value, max_length)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_length)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, max_length) if isinstance(item, dict)
                else sanitize_string(item, max_length) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def log_security_event(
    event_type: str,
    user_id: str = None,
    action: str = None,
    status: str = "success",
    details: str = None,
):
    """Log security events for audit trail."""
    event_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "action": action,
        "status": status,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "unknown"),
        "details": details,
    }
    logger.info(f"SECURITY_EVENT: {event_data}")


def require_auth(f):
    """Decorator to require JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get("AUTH_ENABLED", True):
            return f(*args, **kwargs)

        token = extract_token_from_request()
        if not token:
            log_security_event(
                "auth_attempt", status="failed", details="No token provided"
            )
            return jsonify({"detail": "Missing authorization token"}), 401

        try:
            payload = verify_jwt_token(token)
            request.user_id = payload["user_id"]
            request.user_roles = payload.get("roles", [])
            log_security_event(
                "auth_success", user_id=payload["user_id"], action=f.__name__
            )
            return f(*args, **kwargs)
        except ValueError as e:
            log_security_event(
                "auth_attempt",
                status="failed",
                details=str(e),
            )
            return jsonify({"detail": str(e)}), 401

    return decorated_function


def require_role(*required_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get("AUTH_ENABLED", True):
                return f(*args, **kwargs)

            user_roles = getattr(request, "user_roles", [])
            if not any(role in user_roles for role in required_roles):
                log_security_event(
                    "authorization_failed",
                    user_id=getattr(request, "user_id", None),
                    action=f.__name__,
                    details=f"Required roles: {required_roles}, User roles: {user_roles}",
                )
                return (
                    jsonify({"detail": "Insufficient permissions"}),
                    403,
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator
