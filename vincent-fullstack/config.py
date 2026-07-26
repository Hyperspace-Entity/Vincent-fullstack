# Re-export from the canonical location so any external tooling that imports
# this top-level module gets the same Config as the app package itself.
from app.config import Config  # noqa: F401
