"""Health-Link Flask application factory."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import click
from flask import Flask

from app.config import CONFIGS, finalize_secrets
from app.extensions import bcrypt, cors, db, jwt, migrate
from app.middleware import register_error_handlers, register_jwt_callbacks, register_security_headers
from app.services.model_registry import ModelRegistry
from app.utils.rate_limit import SlidingWindowLimiter


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    config_name = config_name or os.getenv("FLASK_ENV_NAME", "development")
    app = Flask(__name__, instance_path=str(Path(__file__).resolve().parents[1] / "instance"))
    app.config.from_object(CONFIGS[config_name])
    app.config["ENV_NAME"] = config_name
    if overrides:
        app.config.update(overrides)
    finalize_secrets(app)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///") and ":memory:" not in app.config["SQLALCHEMY_DATABASE_URI"]:
        Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)

    register_jwt_callbacks()
    register_error_handlers(app)
    register_security_headers(app)

    from app.routes.auth import bp as auth_bp
    from app.routes.predictions import bp as predictions_bp
    from app.routes.system import admin_bp, health_bp, ocr_bp

    for bp in (auth_bp, predictions_bp, health_bp, ocr_bp, admin_bp):
        app.register_blueprint(bp)

    registry = ModelRegistry()
    registry.load_all(app.config["MODEL_DIR"])
    app.extensions["model_registry"] = registry
    app.extensions["login_limiter"] = SlidingWindowLimiter()

    from app import models  # noqa: F401  (register tables)
    if app.config["AUTO_CREATE_TABLES"]:
        # Convenient default for SQLite demos. Set AUTO_CREATE_TABLES=false to
        # manage the schema with Flask-Migrate (flask db upgrade) instead.
        with app.app_context():
            db.create_all()

    if app.config.get("ADMIN_EMAIL") and app.config.get("ADMIN_PASSWORD") and not app.config["TESTING"]:
        with app.app_context():
            ensure_admin(app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"], app.config.get("ADMIN_NAME") or "Administrator")

    _register_cli(app)
    return app


def ensure_admin(email: str, password: str, name: str = "Administrator") -> str:
    """Create the configured admin account if it does not exist, or promote an
    existing account with that email to admin. An existing password is never
    changed. Returns "created", "promoted" or "exists"."""
    from app.models import User
    email = email.strip().lower()
    try:
        user = User.query.filter_by(email=email).first()
    except Exception:  # tables not created yet (e.g. before `flask db upgrade`)
        db.session.rollback()
        return "skipped"
    if user is None:
        db.session.add(User(name=name, email=email, role="admin",
                            password_hash=bcrypt.generate_password_hash(password).decode()))
        db.session.commit()
        logging.getLogger("healthlink").info("Created admin account %s from configuration", email)
        return "created"
    if user.role != "admin" or not user.is_active:
        user.role, user.is_active = "admin", True
        db.session.commit()
        logging.getLogger("healthlink").info("Promoted %s to admin from configuration", email)
        return "promoted"
    return "exists"


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (idempotent)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True, default="Administrator")
    @click.password_option()
    def create_admin(email, name, password):
        """Create an admin user, or promote an existing user to admin."""
        from app.models import User
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = "admin"
            click.echo(f"Promoted existing user {email} to admin.")
        else:
            if len(password) < 8:
                raise click.BadParameter("Password must be at least 8 characters.")
            user = User(name=name, email=email, role="admin",
                        password_hash=bcrypt.generate_password_hash(password).decode())
            db.session.add(user)
            click.echo(f"Created admin {email}.")
        db.session.commit()
