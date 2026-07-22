from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    # Dev only — restrict this to your real frontend origin before production
    CORS(app)

    from app.review_queue import review_queue_bp
    app.register_blueprint(review_queue_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()  # fine for early dev; switch to Flask-Migrate once this matters

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
