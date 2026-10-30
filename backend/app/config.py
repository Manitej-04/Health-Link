"""Application configuration loaded from environment variables (.env)."""

from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

log = logging.getLogger(__name__)

PLACEHOLDER_SECRETS = {"", "change-me", "replace-with-a-long-random-string"}


def _secret(name: str) -> str | None:
    value = os.getenv(name, "")
    return None if value in PLACEHOLDER_SECRETS else value


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    APP_NAME = "Health-Link"
    SECRET_KEY = _secret("SECRET_KEY")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'instance' / 'healthlink.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Authentication: JWT stored in an HttpOnly cookie + double-submit CSRF token.
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "120")))
    JWT_COOKIE_SECURE = _bool("JWT_COOKIE_SECURE", False)
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_PATH = "/api/"
    JWT_CSRF_IN_COOKIES = True

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    MODEL_DIR = Path(os.getenv("MODEL_DIR", str(BACKEND_DIR / "ml" / "artifacts")))

    # Application-defined educational risk bands applied to calibrated model
    # probabilities. These are NOT clinical thresholds.
    RISK_LOW_MAX = float(os.getenv("RISK_LOW_MAX", "0.30"))
    RISK_MODERATE_MAX = float(os.getenv("RISK_MODERATE_MAX", "0.70"))

    LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
    LOGIN_RATE_WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "300"))

    AUTO_CREATE_TABLES = _bool("AUTO_CREATE_TABLES", True)

    # Optional: admin account created automatically at startup if missing.
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrator")

    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SECRET_KEY = "test-secret-key-not-for-production-use-0123456789"
    JWT_SECRET_KEY = "test-jwt-secret-not-for-production-use-0123456789"
    LOGIN_RATE_LIMIT = 1000
    AUTO_CREATE_TABLES = True


class ProductionConfig(BaseConfig):
    JWT_COOKIE_SECURE = _bool("JWT_COOKIE_SECURE", True)


CONFIGS = {"development": DevelopmentConfig, "testing": TestingConfig, "production": ProductionConfig}


def finalize_secrets(app) -> None:
    """Refuse to run production without real secrets; use ephemeral random
    secrets in development (sessions reset on restart) with a warning."""
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        if not app.config.get(key):
            if app.config.get("ENV_NAME") == "production":
                raise RuntimeError(f"{key} must be set in the environment for production")
            app.config[key] = secrets.token_hex(32)
            log.warning("%s not set; using an ephemeral random value (logins reset on restart). "
                        "Set it in backend/.env.", key)
