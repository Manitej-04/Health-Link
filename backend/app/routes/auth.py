from datetime import datetime, timezone

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    current_user,
    get_jwt,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from sqlalchemy.exc import IntegrityError

from app.extensions import bcrypt, db
from app.models import TokenBlocklist, User, utcnow
from app.schemas import ChangePasswordSchema, LoginSchema, ProfileSchema, RegisterSchema, load_or_400
from app.utils.responses import ApiError, ok

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Used to keep login timing similar whether or not the email exists.
_DUMMY_HASH = None


def _dummy_hash():
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = bcrypt.generate_password_hash("not-a-real-password-1").decode()
    return _DUMMY_HASH


def _session_response(user: User, status: int = 200):
    resp, code = ok({"user": user.to_dict()}, status)
    set_access_cookies(resp, create_access_token(identity=user))
    return resp, code


@bp.post("/register")
def register():
    data = load_or_400(RegisterSchema(), request.get_json(silent=True))
    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        raise ApiError("email_taken", "An account with this email already exists.", 409,
                       {"email": "An account with this email already exists."})
    user = User(name=data["name"].strip(), email=email,
                password_hash=bcrypt.generate_password_hash(data["password"]).decode())
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError("email_taken", "An account with this email already exists.", 409,
                       {"email": "An account with this email already exists."})
    current_app.logger.info("New user registered id=%s", user.id)
    return _session_response(user, 201)


@bp.post("/login")
def login():
    data = load_or_400(LoginSchema(), request.get_json(silent=True))
    email = data["email"].strip().lower()
    key = f"{request.remote_addr}|{email}"
    login_limiter = current_app.extensions["login_limiter"]
    allowed, retry = login_limiter.hit(key, current_app.config["LOGIN_RATE_LIMIT"],
                                       current_app.config["LOGIN_RATE_WINDOW_SECONDS"])
    if not allowed:
        raise ApiError("too_many_requests", f"Too many sign-in attempts. Try again in {retry} seconds.", 429)

    user = User.query.filter_by(email=email).first()
    valid = bcrypt.check_password_hash(user.password_hash if user else _dummy_hash(), data["password"])
    if not user or not valid:
        raise ApiError("invalid_credentials", "Incorrect email or password.", 401)
    if not user.is_active:
        raise ApiError("account_disabled", "This account has been deactivated. Contact an administrator.", 403)

    current_app.extensions["login_limiter"].reset(key)
    user.last_login_at = utcnow()
    db.session.commit()
    return _session_response(user)


@bp.post("/logout")
@jwt_required()
def logout():
    claims = get_jwt()
    db.session.add(TokenBlocklist(jti=claims["jti"],
                                  expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc).replace(tzinfo=None)))
    # Opportunistic clean-up of expired entries.
    TokenBlocklist.query.filter(TokenBlocklist.expires_at < utcnow()).delete()
    db.session.commit()
    resp, code = ok({"message": "Signed out."})
    unset_jwt_cookies(resp)
    return resp, code


@bp.get("/me")
@jwt_required()
def me():
    return ok({"user": current_user.to_dict()})


@bp.patch("/me")
@jwt_required()
def update_profile():
    data = load_or_400(ProfileSchema(), request.get_json(silent=True))
    current_user.name = data["name"].strip()
    db.session.commit()
    return ok({"user": current_user.to_dict()})


@bp.post("/change-password")
@jwt_required()
def change_password():
    data = load_or_400(ChangePasswordSchema(), request.get_json(silent=True))
    if not bcrypt.check_password_hash(current_user.password_hash, data["current_password"]):
        raise ApiError("validation_error", "Current password is incorrect.", 400,
                       {"current_password": "Current password is incorrect."})
    current_user.password_hash = bcrypt.generate_password_hash(data["new_password"]).decode()
    db.session.commit()
    return ok({"message": "Password updated."})
