"""Prediction, history and report endpoints. Every lookup is scoped to the
authenticated user on the server, so one user can never read another's data."""

from flask import Blueprint, current_app, request
from flask_jwt_extended import current_user, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.middleware import patient_required
from app.models import Prediction, iso
from app.services.model_registry import get_registry
from app.services.prediction_service import DISCLAIMER, run_prediction
from app.services.risk import bands_from_config
from app.services.validation import validate_features
from app.utils.responses import ApiError, ok
from ml.feature_specs import DISEASES, DISEASE_KEYS

bp = Blueprint("predictions", __name__, url_prefix="/api")


@bp.get("/models")
def list_models():
    """Public: module availability, input schemas and evaluation summary."""
    return ok({
        "modules": get_registry().summary(),
        "risk_bands": bands_from_config(current_app.config).describe(),
        "disclaimer": DISCLAIMER,
    })


@bp.post("/predict/<disease>")
@patient_required
def predict(disease):
    if disease not in DISEASES:
        raise ApiError("unknown_disease", f"Unknown disease module '{disease}'.", 404)
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("validation_error", "Request body must be a JSON object with a 'features' object.", 400)
    clean, not_provided = validate_features(disease, body.get("features"))
    source = body.get("source", "manual")
    if source not in ("manual", "ocr"):
        source = "manual"

    result = run_prediction(disease, clean, not_provided)

    pred = Prediction(
        user_id=current_user.id, disease=disease, input_data=clean, not_provided=not_provided,
        predicted_class=result["predicted_class"], predicted_label=result["predicted_label"],
        probability=result["probability"], risk_category=result["risk_category"],
        model_status=result["model_status"], model_algorithm=result["model_algorithm"] or "",
        model_version=result["model_version"] or "", factors=result.get("factors"), source=source,
    )
    db.session.add(pred)
    db.session.commit()
    result["id"] = pred.id
    result["created_at"] = iso(pred.created_at)
    return ok(result, 201)


def _own_prediction_or_404(pred_id: int) -> Prediction:
    # Filtering by user_id means another user's record is indistinguishable
    # from a non-existent one (404, not 403), so IDs cannot be probed.
    pred = Prediction.query.filter_by(id=pred_id, user_id=current_user.id).first()
    if pred is None:
        raise ApiError("not_found", "Prediction not found.", 404)
    return pred


@bp.get("/history")
@patient_required
def history():
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, max(1, int(request.args.get("per_page", 10))))
    except ValueError:
        raise ApiError("validation_error", "page and per_page must be integers.", 400)
    q = Prediction.query.filter_by(user_id=current_user.id)
    disease = request.args.get("disease")
    if disease:
        if disease not in DISEASES:
            raise ApiError("validation_error", "Unknown disease filter.", 400)
        q = q.filter_by(disease=disease)
    pg = q.order_by(Prediction.created_at.desc(), Prediction.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return ok({
        "items": [p.to_summary() for p in pg.items],
        "page": pg.page, "per_page": pg.per_page, "total": pg.total, "pages": pg.pages,
    })


@bp.get("/history/summary")
@patient_required
def history_summary():
    uid = current_user.id
    by_disease = dict(db.session.query(Prediction.disease, func.count(Prediction.id))
                      .filter_by(user_id=uid).group_by(Prediction.disease).all())
    by_risk_rows = (db.session.query(Prediction.disease, Prediction.risk_category, func.count(Prediction.id))
                    .filter_by(user_id=uid).group_by(Prediction.disease, Prediction.risk_category).all())
    by_risk = {d: {"LOW": 0, "MODERATE": 0, "HIGH": 0, "NONE": 0} for d in DISEASE_KEYS}
    for d, r, c in by_risk_rows:
        by_risk[d][r or "NONE"] = c
    recent = (Prediction.query.filter_by(user_id=uid)
              .order_by(Prediction.created_at.desc(), Prediction.id.desc()).limit(5).all())
    trend = (Prediction.query.filter(Prediction.user_id == uid, Prediction.probability.isnot(None))
             .order_by(Prediction.created_at.asc()).limit(200).all())
    return ok({
        "total": sum(by_disease.values()),
        "by_disease": {d: by_disease.get(d, 0) for d in DISEASE_KEYS},
        "by_risk": by_risk,
        "recent": [p.to_summary() for p in recent],
        "probability_trend": [{"id": p.id, "disease": p.disease, "probability": p.probability,
                               "created_at": iso(p.created_at)} for p in trend],
    })


@bp.get("/history/<int:pred_id>")
@patient_required
def history_item(pred_id):
    return ok(_own_prediction_or_404(pred_id).to_dict())


@bp.delete("/history/<int:pred_id>")
@patient_required
def delete_history_item(pred_id):
    pred = _own_prediction_or_404(pred_id)
    db.session.delete(pred)
    db.session.commit()
    return ok({"deleted": pred_id})


def build_report(pred: Prediction) -> dict:
    """Printable report data for one prediction (used by owner and admin views)."""
    spec = DISEASES[pred.disease]
    entry = get_registry().get(pred.disease)
    inputs = []
    for f in spec["features"]:
        v = (pred.input_data or {}).get(f["name"])
        display = "Not provided" if v is None else next(
            (o["label"] for o in f.get("options", []) if float(o["value"]) == float(v)), v)
        inputs.append({"feature": f["name"], "label": f["label"], "value": v, "display": display, "unit": f.get("unit")})
    bands = bands_from_config(current_app.config)
    return {
        "report_id": f"HL-{pred.created_at:%Y%m%d}-{pred.id:05d}",
        "generated_for": {"name": pred.user.name, "email": pred.user.email},
        "prediction": pred.to_dict(),
        "disease_name": spec["name"],
        "inputs": inputs,
        "risk_bands": bands.describe() if pred.probability is not None else None,
        "model": {
            "algorithm": pred.model_algorithm,
            "version": pred.model_version,
            "status_at_prediction": pred.model_status,
            "dataset": spec["dataset"],
            "current_metrics": (entry.public_info().get("metrics") if entry else None),
        },
        "disclaimer": DISCLAIMER,
    }


@bp.get("/reports/<int:pred_id>")
@patient_required
def report(pred_id):
    return ok(build_report(_own_prediction_or_404(pred_id)))
