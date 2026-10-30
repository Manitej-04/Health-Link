import json

import numpy as np
import pandas as pd
import pytest

from app.models import Prediction
from ml.feature_specs import feature_names
from tests.conftest import SAMPLES


def _predict(api, disease, features=None, **extra):
    return api.post(f"/api/predict/{disease}", {"features": SAMPLES[disease] if features is None else features, **extra})


def test_models_endpoint_lists_schema_and_status(client):
    r = client.get("/api/models")
    assert r.status_code == 200
    data = r.get_json()["data"]
    mods = {m["key"]: m for m in data["modules"]}
    assert mods["heart"]["status"] == "available" and mods["heart"]["probability_supported"] is True
    assert mods["kidney"]["status"] == "available" and mods["kidney"]["probability_supported"] is True
    # Integrity findings stay visible as documented data caveats.
    assert any("missing values" in c for c in mods["kidney"]["data_caveats"])
    assert [f["name"] for f in mods["liver"]["features"]] == feature_names("liver")
    assert data["risk_bands"][0]["category"] == "LOW"
    assert "educational prototype" in data["disclaimer"]


@pytest.mark.parametrize("disease", ["heart", "diabetes", "liver"])
def test_probability_modules_return_calibrated_probability_and_risk(user_api, app, disease):
    r = _predict(user_api, disease)
    assert r.status_code == 201, r.get_json()
    res = r.get_json()["data"]
    assert 0.0 <= res["probability"] <= 1.0
    # Probability must equal the model's own output (not a derived/fake number).
    model = app.extensions["model_registry"].get(disease).model
    row = {k: (np.nan if v is None else float(v)) for k, v in SAMPLES[disease].items()}
    expected = model.predict_proba(pd.DataFrame([row], columns=feature_names(disease)))[0, 1]
    assert res["probability"] == pytest.approx(expected, abs=1e-4)
    expected_risk = "LOW" if expected < 0.30 else "MODERATE" if expected < 0.70 else "HIGH"
    assert res["risk_category"] == expected_risk
    assert res["predicted_class"] == int(expected >= 0.5)
    assert "educational" in res["disclaimer"] and res["explanation"]
    assert res["id"] and res["created_at"]


@pytest.mark.parametrize("disease", ["kidney"])
def test_kidney_returns_probability_and_discloses_optional_fields(user_api, disease):
    r = _predict(user_api, disease)
    assert r.status_code == 201
    res = r.get_json()["data"]
    assert 0.0 <= res["probability"] <= 1.0 and res["risk_category"] in ("LOW", "MODERATE", "HIGH")
    assert res["model_status"] == "available" and "experimental_notice" not in res
    assert {n["feature"] for n in res["not_provided"]} == {"rbc", "sod", "pot"}
    assert "median" in res["imputation_notice"]


def test_experimental_status_returns_class_only(make_app, isolated_artifacts):
    """If a module is ever marked experimental, it must show the class only."""
    meta_path = isolated_artifacts / "kidney" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta.update(status="experimental", status_reasons=["test reason"], probability_supported=False,
                probability_reason="withheld for test")
    meta_path.write_text(json.dumps(meta))
    app = make_app(MODEL_DIR=isolated_artifacts)
    from tests.conftest import Api
    a = Api(app.test_client()); a.register()
    res = _predict(a, "kidney").get_json()["data"]
    assert res["probability"] is None and res["risk_category"] is None
    assert "EXPERIMENTAL" in res["experimental_notice"] and res["risk_unavailable_reason"] == "withheld for test"


def test_heart_result_includes_model_factors(user_api):
    res = _predict(user_api, "heart").get_json()["data"]
    assert res["factors"] and all(f["direction"] in ("increases", "decreases") for f in res["factors"])


def test_prediction_is_persisted(user_api, app):
    res = _predict(user_api, "diabetes", source="ocr").get_json()["data"]
    with app.app_context():
        p = Prediction.query.get(res["id"])
        assert p.disease == "diabetes" and p.source == "ocr"
        assert p.probability == res["probability"] and p.risk_category == res["risk_category"]
        assert p.input_data["glucose"] == 148 and p.not_provided == ["insulin"]


def test_invalid_input_rejected_and_not_saved(user_api, app):
    bad = dict(SAMPLES["heart"], chol=5000)
    r = _predict(user_api, "heart", bad)
    assert r.status_code == 400 and "chol" in r.get_json()["error"]["details"]
    with app.app_context():
        assert Prediction.query.count() == 0


def test_missing_features_object(user_api):
    r = user_api.post("/api/predict/heart", {"wrong": 1})
    assert r.status_code == 400


def test_unknown_disease(user_api):
    assert _predict(user_api, "lung", {}).status_code == 404


# ---------- missing / corrupt artifacts ----------

def test_missing_artifact_makes_module_unavailable(make_app, isolated_artifacts):
    (isolated_artifacts / "liver" / "model.joblib").unlink()
    app = make_app(MODEL_DIR=isolated_artifacts)
    from tests.conftest import Api
    a = Api(app.test_client()); a.register()
    r = _predict(a, "liver")
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "model_unavailable"
    mods = {m["key"]: m for m in a.get("/api/models").get_json()["data"]["modules"]}
    assert mods["liver"]["status"] == "unavailable" and mods["heart"]["status"] == "available"


def test_corrupt_artifact_fails_integrity_check(make_app, isolated_artifacts):
    (isolated_artifacts / "heart" / "model.joblib").write_bytes(b"corrupted bytes")
    app = make_app(MODEL_DIR=isolated_artifacts)
    entry = app.extensions["model_registry"].get("heart")
    assert entry.status == "unavailable" and "integrity" in entry.reason


def test_corrupt_pickle_with_matching_checksum_is_caught(make_app, isolated_artifacts):
    import hashlib
    path = isolated_artifacts / "diabetes" / "model.joblib"
    path.write_bytes(b"not a pickle at all")
    meta_path = isolated_artifacts / "diabetes" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(meta))
    app = make_app(MODEL_DIR=isolated_artifacts)
    entry = app.extensions["model_registry"].get("diabetes")
    assert entry.status == "unavailable" and "could not be loaded" in entry.reason


def test_version_mismatch_marks_unavailable(make_app, isolated_artifacts):
    meta_path = isolated_artifacts / "heart" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["environment"]["scikit_learn"] = "0.0.1"
    meta_path.write_text(json.dumps(meta))
    entry = make_app(MODEL_DIR=isolated_artifacts).extensions["model_registry"].get("heart")
    assert entry.status == "unavailable" and "Retrain" in entry.reason


def test_schema_mismatch_marks_unavailable(make_app, isolated_artifacts):
    meta_path = isolated_artifacts / "liver" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["features"] = meta["features"][:-1]
    meta_path.write_text(json.dumps(meta))
    entry = make_app(MODEL_DIR=isolated_artifacts).extensions["model_registry"].get("liver")
    assert entry.status == "unavailable"


def test_probability_withheld_when_not_supported(make_app, isolated_artifacts):
    meta_path = isolated_artifacts / "heart" / "metadata.json"
    meta = json.loads(meta_path.read_text())
    meta["probability_supported"] = False
    meta["probability_reason"] = "Calibration criteria not met (test)"
    meta_path.write_text(json.dumps(meta))
    app = make_app(MODEL_DIR=isolated_artifacts)
    from tests.conftest import Api
    a = Api(app.test_client()); a.register()
    res = _predict(a, "heart").get_json()["data"]
    assert res["probability"] is None and res["risk_category"] is None
    assert res["risk_unavailable_reason"] == "Calibration criteria not met (test)"
