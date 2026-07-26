"""Authentication routes for JWT token management."""

import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from app.extensions import db, limiter
from app.auth.models import User, UserRole
from app.schemas import LoginRequest, TokenResponse, UserCreateRequest, UserResponse
from app.security import (
    generate_jwt_token,
    verify_jwt_token,
    extract_token_from_request,
    require_auth,
    require_role,
    log_security_event,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5/hour")  # Rate limit registration
def register():
    """Register a new user."""
    try:
        payload = request.get_json(force=True)
        user_data = UserCreateRequest(**payload)
    except ValidationError as e:
        log_security_event("registration_failed", details=str(e))
        return jsonify({"detail": "Invalid request data", "errors": e.errors()}), 400

    # Check if user already exists
    if User.query.filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first():
        log_security_event(
            "registration_failed",
            details=f"Username or email already exists",
        )
        return jsonify({"detail": "Username or email already exists"}), 409

    try:
        user = User(
            username=user_data.username,
            email=user_data.email,
            roles=",".join(user_data.roles or [UserRole.REVIEWER.value]),
        )
        user.set_password(user_data.password)
        db.session.add(user)
        db.session.commit()

        log_security_event(
            "user_registered",
            user_id=user.id,
            action="register",
        )

        return jsonify(UserResponse(**user.to_dict()).dict()), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        log_security_event(
            "registration_failed",
            details=f"Internal error: {str(e)}",
        )
        return jsonify({"detail": "Registration failed"}), 500


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")  # Rate limit login attempts
def login():
    """Authenticate user and return JWT tokens."""
    try:
        payload = request.get_json(force=True)
        login_data = LoginRequest(**payload)
    except ValidationError as e:
        log_security_event(
            "login_failed",
            details="Invalid credentials format",
        )
        return jsonify({"detail": "Invalid request data"}), 400

    user = User.query.filter_by(username=login_data.username).first()
    if not user or not user.verify_password(login_data.password):
        log_security_event(
            "login_failed",
            details=f"Invalid credentials for user: {login_data.username}",
        )
        return jsonify({"detail": "Invalid username or password"}), 401

    if not user.is_active:
        log_security_event(
            "login_failed",
            user_id=user.id,
            details="User account is inactive",
        )
        return jsonify({"detail": "User account is inactive"}), 403

    try:
        user.last_login = datetime.utcnow()
        db.session.commit()

        access_token = generate_jwt_token(
            user_id=user.id,
            roles=user.get_roles_list(),
            token_type="access",
        )
        refresh_token = generate_jwt_token(
            user_id=user.id,
            roles=user.get_roles_list(),
            expires_in=60 * 60 * 24 * 30,  # 30 days
            token_type="refresh",
        )

        log_security_event(
            "login_success",
            user_id=user.id,
            action="login",
        )

        response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=3600,
        )
        return jsonify(response.dict()), 200
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        log_security_event(
            "login_failed",
            user_id=user.id,
            details=f"Internal error: {str(e)}",
        )
        return jsonify({"detail": "Login failed"}), 500


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("30/hour")
def refresh():
    """Refresh an access token using a refresh token."""
    token = extract_token_from_request()
    if not token:
        return jsonify({"detail": "Missing refresh token"}), 401

    try:
        payload = verify_jwt_token(token)

        if payload.get("token_type") != "refresh":
            raise ValueError("Token is not a refresh token")

        user = User.query.get(payload["user_id"])
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        access_token = generate_jwt_token(
            user_id=user.id,
            roles=user.get_roles_list(),
            token_type="access",
        )

        response = TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=3600,
        )
        return jsonify(response.dict()), 200
    except ValueError as e:
        log_security_event(
            "token_refresh_failed",
            details=str(e),
        )
        return jsonify({"detail": str(e)}), 401


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Get current authenticated user."""
    user = User.query.get(request.user_id)
    if not user:
        return jsonify({"detail": "User not found"}), 404

    return jsonify(UserResponse(**user.to_dict()).dict()), 200


@auth_bp.route("/users", methods=["GET"])
@require_auth
@require_role(UserRole.ADMIN.value)
def list_users():
    """List all users (admin only)."""
    users = User.query.all()
    return (
        jsonify([UserResponse(**user.to_dict()).dict() for user in users]),
        200,
    )


@auth_bp.route("/users/<user_id>", methods=["GET"])
@require_auth
def get_user(user_id):
    """Get specific user (admin only or self)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"detail": "User not found"}), 404

    if request.user_id != user_id and "admin" not in request.user_roles:
        return jsonify({"detail": "Insufficient permissions"}), 403

    return jsonify(UserResponse(**user.to_dict()).dict()), 200


@auth_bp.route("/users/<user_id>/activate", methods=["POST"])
@require_auth
@require_role(UserRole.ADMIN.value)
def activate_user(user_id):
    """Activate a user (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"detail": "User not found"}), 404

    user.is_active = True
    db.session.commit()

    log_security_event(
        "user_activated",
        user_id=user_id,
        action="activate",
    )

    return jsonify(UserResponse(**user.to_dict()).dict()), 200


@auth_bp.route("/users/<user_id>/deactivate", methods=["POST"])
@require_auth
@require_role(UserRole.ADMIN.value)
def deactivate_user(user_id):
    """Deactivate a user (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"detail": "User not found"}), 404

    user.is_active = False
    db.session.commit()

    log_security_event(
        "user_deactivated",
        user_id=user_id,
        action="deactivate",
    )

    return jsonify(UserResponse(**user.to_dict()).dict()), 200
