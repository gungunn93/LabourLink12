import os
from flask import Flask, jsonify, send_from_directory

from config import Config
from extensions import db, jwt, cors, socketio
from schema_sync import sync_schema
from models import User, JobCategory


def _build_origins(app):
    """Return a list of allowed origins from config."""
    raw = app.config.get("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]

    # Also honour the legacy FRONTEND_ORIGIN single-value env var
    legacy = app.config.get("FRONTEND_ORIGIN", "").strip()
    if legacy and legacy not in origins:
        origins.append(legacy)

    # In development, always allow local Vite dev server
    if app.config.get("APP_ENV") == "development":
        for local in (
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ):
            if local not in origins:
                origins.append(local)

    return origins if origins else "*"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)

    origins = _build_origins(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {"origins": origins},
            r"/socket.io/*": {"origins": origins},
        },
        supports_credentials=True,
    )
    # Pass the same origin list to Socket.IO so WebSocket upgrades are also gated
    # async_mode is already set on the socketio instance in extensions.py
    socketio.init_app(
        app,
        cors_allowed_origins=origins,
        logger=False,
        engineio_logger=False,
        ping_timeout=60,
        ping_interval=25,
    )

    from routes.auth import auth_bp
    from routes.jobs import jobs_bp
    from routes.applications import applications_bp
    from routes.negotiations import negotiations_bp
    from routes.chat import chat_bp
    from routes.payments import payments_bp
    from routes.location import location_bp
    from routes.extra_work import extra_bp
    from routes.workers import workers_bp
    from routes.employers import employers_bp
    from routes.ratings import ratings_bp
    from routes.notifications import notifications_bp
    from routes.uploads import uploads_bp
    from routes.admin import admin_bp
    from routes.reports import reports_bp
    import sockets  # noqa: F401  — registers Socket.IO event handlers

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    for blueprint in (
        jobs_bp,
        applications_bp,
        negotiations_bp,
        chat_bp,
        payments_bp,
        location_bp,
        extra_bp,
        workers_bp,
        employers_bp,
        ratings_bp,
        notifications_bp,
        uploads_bp,
        admin_bp,
        reports_bp,
    ):
        app.register_blueprint(blueprint, url_prefix="/api")

    @app.get("/api/health")
    def health():
        return jsonify(
            success=True,
            message="Operation successful",
            data={
                "service": "LabourLink",
                "status": "running",
                "env": app.config.get("APP_ENV"),
                "payment_gateway": app.config.get("PAYMENT_GATEWAY"),
            },
        )

    @app.get("/uploads/<path:name>")
    def uploaded(name):
        return send_from_directory(app.config["UPLOAD_FOLDER"], name)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify(success=False, message="Resource not found"), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify(success=False, message="HTTP method not allowed"), 405

    @app.errorhandler(500)
    def internal_server_error(_error):
        db.session.rollback()
        return jsonify(success=False, message="Internal server error"), 500

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify(success=False, message="Authorization token required"), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify(success=False, message="Invalid or expired token"), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify(success=False, message="Session expired. Please log in again."), 401

    return app


def initialize_database(app):
    with app.app_context():
        db.create_all()
        try:
            sync_schema()
        except Exception:
            app.logger.exception("Schema sync skipped")
            db.session.rollback()
        defaults = [
            "Painting", "Plumbing", "Electrical", "Carpentry", "Cleaning",
            "Masonry", "Construction", "Gardening", "Moving", "Other",
        ]
        for name in defaults:
            if not JobCategory.query.filter_by(name=name).first():
                db.session.add(JobCategory(name=name))
        db.session.commit()


app = create_app()


if __name__ == "__main__":
    initialize_database(app)
    # Local development only — never runs in production (gunicorn is used instead)
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        debug=False,
        use_reloader=False,
    )
