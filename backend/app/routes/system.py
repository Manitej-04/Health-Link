from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_, text

from app.extensions import db
from app.middleware import admin_required, patient_required
from app.models import Prediction, User
from app.schemas import AdminUserUpdateSchema, load_or_400
from app.services import ocr_service
from app.services.model_registry import get_registry
from app.utils.responses import ApiError, ok
from flask_jwt_extended import current_user
from ml.feature_specs import DISEASE_KEYS

health_bp = Blueprint("health", __name__, url_prefix="/api")
ocr_bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@health_bp.get("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    modules = {e["key"]: e["status"] for e in get_registry().summary()}
    return ok({"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "error", "models": modules},
              200 if db_ok else 503)


@ocr_bp.post("/extract")
@patient_required
def ocr_extract():
    disease = request.form.get("disease", "")
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ApiError("validation_error", "Attach a report file in the 'file' field.", 400)
    data = upload.read()
    return ok(ocr_service.extract(data, upload.filename, disease))


@admin_bp.get("/stats")
@admin_required
def admin_stats():
    by_disease = dict(db.session.query(Prediction.disease, func.count(Prediction.id)).group_by(Prediction.disease).all())
    by_risk = dict(db.session.query(Prediction.risk_category, func.count(Prediction.id)).group_by(Prediction.risk_category).all())
    return ok({
        "users": {"total": User.query.count(), "active": User.query.filter_by(is_active=True).count(),
                  "admins": User.query.filter_by(role="admin").count()},
        "predictions": {
            "total": Prediction.query.count(),
            "by_disease": {d: by_disease.get(d, 0) for d in DISEASE_KEYS},
            "by_risk": {"LOW": by_risk.get("LOW", 0), "MODERATE": by_risk.get("MODERATE", 0),
                        "HIGH": by_risk.get("HIGH", 0), "NONE": by_risk.get(None, 0)},
        },
        "models": get_registry().summary(),
    })


@admin_bp.get("/analytics")
@admin_required
def admin_analytics():
    """Disease-wise analysis across all patients."""
    from datetime import timedelta
    from app.models import utcnow
    diseases = {}
    for d in DISEASE_KEYS:
        base = Prediction.query.filter(Prediction.disease == d)
        total = base.count()
        positive = base.filter(Prediction.predicted_class == 1).count()
        patients = db.session.query(func.count(func.distinct(Prediction.user_id))).filter(Prediction.disease == d).scalar()
        avg_prob = db.session.query(func.avg(Prediction.probability)).filter(
            Prediction.disease == d, Prediction.probability.isnot(None)).scalar()
        risk = dict(db.session.query(Prediction.risk_category, func.count(Prediction.id))
                    .filter(Prediction.disease == d).group_by(Prediction.risk_category).all())
        diseases[d] = {
            "total": total, "patients": patients or 0, "positive": positive,
            "positive_rate": (positive / total) if total else None,
            "avg_probability": float(avg_prob) if avg_prob is not None else None,
            "by_risk": {"LOW": risk.get("LOW", 0), "MODERATE": risk.get("MODERATE", 0),
                        "HIGH": risk.get("HIGH", 0), "NONE": risk.get(None, 0)},
        }
    since = utcnow() - timedelta(days=29)
    rows = (db.session.query(func.date(Prediction.created_at), Prediction.disease, func.count(Prediction.id))
            .filter(Prediction.created_at >= since).group_by(func.date(Prediction.created_at), Prediction.disease).all())
    days = {}
    for day, d, c in rows:
        days.setdefault(str(day), {k: 0 for k in DISEASE_KEYS})[d] = c
    timeline = []
    for i in range(30):
        day = (since + timedelta(days=i)).date().isoformat()
        timeline.append({"date": day, **days.get(day, {k: 0 for k in DISEASE_KEYS})})
    high_risk_patients = (db.session.query(User.id, User.name, User.email, func.count(Prediction.id))
                          .join(Prediction).filter(Prediction.risk_category == "HIGH")
                          .group_by(User.id).order_by(func.count(Prediction.id).desc()).limit(10).all())
    return ok({
        "diseases": diseases,
        "timeline": timeline,
        "high_risk_patients": [{"id": i, "name": n, "email": e, "high_count": c} for i, n, e, c in high_risk_patients],
    })


@admin_bp.get("/users")
@admin_required
def admin_users():
    counts = dict(db.session.query(Prediction.user_id, func.count(Prediction.id)).group_by(Prediction.user_id).all())
    q = User.query
    if request.args.get("role") in ("user", "admin"):
        q = q.filter(User.role == request.args["role"])
    users = q.order_by(User.created_at.desc()).all()
    return ok({"items": [{**u.to_dict(), "prediction_count": counts.get(u.id, 0)} for u in users]})


def _admin_prediction_row(p: Prediction) -> dict:
    row = p.to_summary()
    row["patient"] = {"id": p.user.id, "name": p.user.name, "email": p.user.email}
    return row


@admin_bp.get("/predictions")
@admin_required
def admin_predictions():
    """Every patient's assessments, newest first. Filters: user_id, disease, risk, q (name/email)."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
        user_id = int(request.args["user_id"]) if request.args.get("user_id") else None
    except ValueError:
        raise ApiError("validation_error", "page, per_page and user_id must be integers.", 400)
    q = Prediction.query.join(User)
    if user_id:
        q = q.filter(Prediction.user_id == user_id)
    disease = request.args.get("disease")
    if disease:
        if disease not in DISEASE_KEYS:
            raise ApiError("validation_error", "Unknown disease filter.", 400)
        q = q.filter(Prediction.disease == disease)
    risk = request.args.get("risk")
    if risk:
        if risk not in ("LOW", "MODERATE", "HIGH", "NONE"):
            raise ApiError("validation_error", "Unknown risk filter.", 400)
        q = q.filter(Prediction.risk_category.is_(None) if risk == "NONE" else Prediction.risk_category == risk)
    text_q = (request.args.get("q") or "").strip()
    if text_q:
        like = f"%{text_q}%"
        q = q.filter(or_(User.name.ilike(like), User.email.ilike(like)))
    pg = q.order_by(Prediction.created_at.desc(), Prediction.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return ok({"items": [_admin_prediction_row(p) for p in pg.items],
               "page": pg.page, "per_page": pg.per_page, "total": pg.total, "pages": pg.pages})


@admin_bp.get("/predictions/<int:pred_id>")
@admin_required
def admin_prediction_detail(pred_id):
    p = db.session.get(Prediction, pred_id)
    if p is None:
        raise ApiError("not_found", "Prediction not found.", 404)
    data = p.to_dict()
    data["patient"] = {"id": p.user.id, "name": p.user.name, "email": p.user.email}
    return ok(data)


@admin_bp.get("/reports/<int:pred_id>")
@admin_required
def admin_report(pred_id):
    from app.routes.predictions import build_report
    p = db.session.get(Prediction, pred_id)
    if p is None:
        raise ApiError("not_found", "Prediction not found.", 404)
    return ok(build_report(p))


@admin_bp.get("/users/<int:user_id>")
@admin_required
def admin_user_detail(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("not_found", "User not found.", 404)
    by_disease = dict(db.session.query(Prediction.disease, func.count(Prediction.id))
                      .filter_by(user_id=user_id).group_by(Prediction.disease).all())
    by_risk = dict(db.session.query(Prediction.risk_category, func.count(Prediction.id))
                   .filter_by(user_id=user_id).group_by(Prediction.risk_category).all())
    return ok({
        "user": user.to_dict(),
        "prediction_count": sum(by_disease.values()),
        "by_disease": {d: by_disease.get(d, 0) for d in DISEASE_KEYS},
        "by_risk": {"LOW": by_risk.get("LOW", 0), "MODERATE": by_risk.get("MODERATE", 0),
                    "HIGH": by_risk.get("HIGH", 0), "NONE": by_risk.get(None, 0)},
    })


@admin_bp.patch("/users/<int:user_id>")
@admin_required
def admin_update_user(user_id):
    data = load_or_400(AdminUserUpdateSchema(), request.get_json(silent=True))
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("not_found", "User not found.", 404)
    if user.id == current_user.id:
        raise ApiError("forbidden", "You cannot change your own role or status.", 403)
    if "is_active" in data:
        user.is_active = data["is_active"]
    if "role" in data:
        user.role = data["role"]
    db.session.commit()
    return ok({"user": user.to_dict()})
