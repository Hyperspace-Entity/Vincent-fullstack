from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    CORS(app)

    from app.review_queue import review_queue_bp
    app.register_blueprint(review_queue_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        return {
            "message": "Vincent Review Queue API",
            "endpoints": {
                "/health": "Health check",
                "/api/queue": "GET/POST documents",
                "/api/queue/<doc_id>": "GET/PATCH specific document"
            }
        }

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
