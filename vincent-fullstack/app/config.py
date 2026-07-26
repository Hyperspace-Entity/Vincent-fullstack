import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)


class Config:
    """Base configuration with security defaults"""

    # Flask
    ENV = os.environ.get("FLASK_ENV", "production")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    TESTING = False

    # Security - NEVER use defaults in production
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-this-in-production-min-32-chars-dev-secret",
    )
    if len(SECRET_KEY) < 32:
        raise ValueError(
            "SECRET_KEY must be at least 32 characters. Set a strong SECRET_KEY in .env"
        )

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'vincent.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "connect_args": {"timeout": 15},
    }

    # JWT
    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        "dev-jwt-secret-key-change-this-in-production-min-32-chars-dev-secret",
    )
    if len(JWT_SECRET_KEY) < 32:
        raise ValueError(
            "JWT_SECRET_KEY must be at least 32 characters. Set a strong JWT_SECRET_KEY in .env"
        )
    JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRES = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)
    )  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = int(
        os.environ.get("JWT_REFRESH_TOKEN_EXPIRES", 2592000)
    )  # 30 days

    # CORS
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5000"
    ).split(",")
    CORS_ALLOW_HEADERS = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
    ]
    CORS_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]

    # Rate Limiting
    RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "100/hour")
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")

    # Request Size Limits
    MAX_CONTENT_LENGTH = int(
        os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )  # 16MB

    # Session Security
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "True"
    ).lower() == "true"
    SESSION_COOKIE_HTTPONLY = os.environ.get(
        "SESSION_COOKIE_HTTPONLY", "True"
    ).lower() == "true"
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FILE = os.environ.get("LOG_FILE", os.path.join(BASE_DIR, "logs", "vincent.log"))

    # Feature Flags
    AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "True").lower() == "true"
    AUDIT_LOGGING_ENABLED = os.environ.get(
        "AUDIT_LOGGING_ENABLED", "True"
    ).lower() == "true"


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG = True
    ENV = "development"
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    RATE_LIMIT_ENABLED = False


class TestingConfig(Config):
    """Testing configuration"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATE_LIMIT_ENABLED = False
    JWT_ACCESS_TOKEN_EXPIRES = 3600


class ProductionConfig(Config):
    """Production configuration with strict security settings"""

    DEBUG = False
    ENV = "production"
    SESSION_COOKIE_SECURE = True
    RATE_LIMIT_ENABLED = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
