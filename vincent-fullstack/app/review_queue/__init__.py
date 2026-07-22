from flask import Blueprint

review_queue_bp = Blueprint("review_queue", __name__)

from . import routes  # noqa: E402,F401
