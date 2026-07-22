"""
Shared Flask extensions. Kept in their own module (rather than inside
__init__.py) so any part of the app can do `from app.extensions import db`
without circular-import headaches.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
