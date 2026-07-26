"""Flask app factory with security middleware and error handling."""

import logging
import logging.handlers
import os
from flask import Flask, jsonify
from flask_cors import CORS

from app.config import config_by_name
from app.extensions import db, limiter


def setup_logging(app: Flask):
    """Configure logging with rotation and structured format."""
    log_level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)
    
    # Create logs directory
    log_dir = os.path.dirname(app.config["LOG_FILE"])
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        app.config["LOG_FILE"],
        maxBytes=10485760,  # 10MB
        backupCount=10,
    )
    file_handler.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)


def setup_security_headers(app: Flask):
    """Add security headers to all responses."""
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
    return app


def setup_error_handlers(app: Flask):
    """Register error handlers for common HTTP errors."""
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"detail": "Bad request", "error_code": "BAD_REQUEST"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"detail": "Unauthorized", "error_code": "UNAUTHORIZED"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"detail": "Forbidden", "error_code": "FORBIDDEN"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"detail": "Not found", "error_code": "NOT_FOUND"}), 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({"detail": "Rate limit exceeded", "error_code": "RATE_LIMIT_EXCEEDED"}), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal error: {str(error)}")
        return jsonify({"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}), 500


def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    
    config_class = config_by_name.get(config_name, config_by_name["development"])
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)
    
    # Setup CORS with secure defaults
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        allow_headers=app.config["CORS_ALLOW_HEADERS"],
        methods=app.config["CORS_METHODS"],
        supports_credentials=True,
        max_age=3600,
    )
    
    # Setup logging
    setup_logging(app)
    
    # Setup security
    setup_security_headers(app)
    setup_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from app.auth import auth_bp
    from app.review_queue import review_queue_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(review_queue_bp, url_prefix="/api")
    
    # Root endpoint
    @app.route("/")
    def index():
        return jsonify({
            "name": "Vincent Review Queue API",
            "version": "2.0.0",
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "auth": "/auth/login",
                "api": "/api/queue",
            },
        }), 200
    
    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({"status": "ok", "version": "2.0.0"}), 200
    
    return app
