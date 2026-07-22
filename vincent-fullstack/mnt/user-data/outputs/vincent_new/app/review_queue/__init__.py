"""
Vincent - Review Queue
------------------------
Matches the API shape the frontend (vincent-app.html) already speaks:
review queue, risk scoring, audit trail, templates, bulk actions, and a
public client status page.
"""

from flask import Blueprint

review_queue_bp = Blueprint("review_queue", __name__)

from . import routes  # noqa: E402,F401 — registers routes on the blueprint above
