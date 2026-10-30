"""Cross-cutting request handling: error handlers, security headers, guards."""

from __future__ import annotations

import logging
from functools import wraps

from flask import request
from flask_jwt_extended import current_user, verify_jwt_in_request
from werkzeug.exceptions import HTTPException

from app.extensions import db, jwt
from app.models import TokenBlocklist, User
from app.utils.responses import ApiError, error

log = logging.getLogger("healthlink")


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def _api_error(e: ApiError):
        return error(e.code, e.message, e.status, e.details)

    @app.errorhandler(HTTPException)
    def _http_error(e: HTTPException):
        codes = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
                 405: "method_not_allowed", 413: "payload_too_large", 415: "unsupported_media_type",
                 429: "too_many_requests"}
        messages = {413: "Uploaded file is too large.", 404: "Resource not found.",
                    405: "Method not allowed.", 400: "Malformed request."}
        return error(codes.get(e.code, "http_error"), messages.get(e.code, e.name), e.code)

    @app.errorhandler(Exception)
    def _unhandled(e: Exception):
        db.session.rollback()
        # Full details go to the server log only; clients never see stack traces.
        log.exception("Unhandled error on %s %s", request.method, request.path)
        return error("internal_error", "An unexpected error occurred. Please try again.", 500)


def register_jwt_callbacks() -> None:
    @jwt.user_identity_loader
    def _identity(user):
        return str(user.id) if isinstance(user, User) else str(user)

    @jwt.user_lookup_loader
    def _lookup(_header, payload):
        user = db.session.get(User, int(payload["sub"]))
        return user if user and user.is_active else None

    @jwt.user_lookup_error_loader
    def _lookup_error(_header, _payload):
        return error("unauthorized", "Your session is no longer valid. Please sign in again.", 401)

    @jwt.token_in_blocklist_loader
    def _revoked(_header, payload) -> bool:
        return db.session.query(TokenBlocklist.id).filter_by(jti=payload["jti"]).first() is not None

    @jwt.revoked_token_loader
    def _revoked_resp(_h, _p):
        return error("unauthorized", "You have been signed out. Please sign in again.", 401)

    @jwt.expired_token_loader
    def _expired(_h, _p):
        return error("token_expired", "Your session has expired. Please sign in again.", 401)

    @jwt.unauthorized_loader
    def _missing(reason):
        if "CSRF" in reason:
            return error("csrf_failed", "Missing or invalid CSRF token.", 401)
        return error("unauthorized", "Authentication required.", 401)

    @jwt.invalid_token_loader
    def _invalid(reason):
        if "CSRF" in reason:
            return error("csrf_failed", "Missing or invalid CSRF token.", 401)
        return error("unauthorized", "Invalid authentication token.", 401)


def register_security_headers(app) -> None:
    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp


def patient_required(fn):
    """Patient-only features (running assessments, own history, OCR). Admin
    accounts manage and review patients' data instead of creating their own."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if current_user and current_user.is_admin:
            raise ApiError("forbidden", "Administrator accounts review patients' assessments and do not run their own.", 403)
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not current_user or not current_user.is_admin:
            raise ApiError("forbidden", "Administrator access required.", 403)
        return fn(*args, **kwargs)

    return wrapper
