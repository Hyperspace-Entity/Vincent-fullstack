import os


def _require_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Provide a PostgreSQL connection string, e.g. "
            "******host:5432/dbname"
        )
    # Heroku and some platforms still emit the legacy 'postgres://' scheme;
    # SQLAlchemy 1.4+ requires 'postgresql://'.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")
    SQLALCHEMY_DATABASE_URI = _require_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
