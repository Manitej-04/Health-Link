from tests.conftest import SAMPLES


def _make(api, disease="heart"):
    r = api.post(f"/api/predict/{disease}", {"features": SAMPLES[disease]})
    assert r.status_code == 201
    return r.get_json()["data"]["id"]


def test_history_pagination_and_filter(user_api):
    ids = [_make(user_api, d) for d in ["heart", "diabetes", "liver", "heart", "kidney"]]
    r = user_api.get("/api/history?page=1&per_page=2").get_json()["data"]
    assert r["total"] == 5 and r["pages"] == 3 and len(r["items"]) == 2
    assert r["items"][0]["id"] == ids[-1]  # newest first
    r = user_api.get("/api/history?disease=heart").get_json()["data"]
    assert r["total"] == 2 and all(i["disease"] == "heart" for i in r["items"])
    assert user_api.get("/api/history?page=abc").status_code == 400
    assert user_api.get("/api/history?disease=lung").status_code == 400


def test_history_summary(user_api):
    _make(user_api, "heart"); _make(user_api, "kidney")
    s = user_api.get("/api/history/summary").get_json()["data"]
    assert s["total"] == 2 and s["by_disease"]["heart"] == 1 and s["by_disease"]["kidney"] == 1
    assert sum(s["by_risk"]["kidney"].values()) == 1 and s["by_risk"]["kidney"]["NONE"] == 0
    assert len(s["recent"]) == 2 and len(s["probability_trend"]) == 2


def test_history_item_and_delete(user_api):
    pid = _make(user_api)
    item = user_api.get(f"/api/history/{pid}").get_json()["data"]
    assert item["input_data"]["chol"] == 286
    assert user_api.delete(f"/api/history/{pid}").status_code == 200
    assert user_api.get(f"/api/history/{pid}").status_code == 404


def test_users_cannot_access_each_others_records(user_api, other_api):
    pid = _make(user_api)
    assert other_api.get(f"/api/history/{pid}").status_code == 404
    assert other_api.get(f"/api/reports/{pid}").status_code == 404
    assert other_api.delete(f"/api/history/{pid}").status_code == 404
    assert other_api.get("/api/history").get_json()["data"]["total"] == 0
    assert other_api.get("/api/history/summary").get_json()["data"]["total"] == 0
    # still intact for the owner
    assert user_api.get(f"/api/history/{pid}").status_code == 200


def test_report_contents(user_api):
    pid = _make(user_api, "diabetes")
    rep = user_api.get(f"/api/reports/{pid}").get_json()["data"]
    assert rep["report_id"].startswith("HL-") and rep["disease_name"] == "Diabetes"
    assert rep["generated_for"]["email"] == "alice@example.com"
    inputs = {i["feature"]: i for i in rep["inputs"]}
    assert inputs["insulin"]["display"] == "Not provided" and inputs["glucose"]["unit"] == "mg/dL"
    assert rep["risk_bands"] and "educational" in rep["disclaimer"]
    assert rep["model"]["algorithm"]


def test_report_select_fields_show_labels(user_api):
    pid = _make(user_api, "heart")
    inputs = {i["feature"]: i for i in user_api.get(f"/api/reports/{pid}").get_json()["data"]["inputs"]}
    assert inputs["sex"]["display"] == "Male" and inputs["cp"]["display"] == "Asymptomatic"


# ---------- admin ----------

def test_non_admin_forbidden(user_api):
    assert user_api.get("/api/admin/stats").status_code == 403
    assert user_api.get("/api/admin/users").status_code == 403


def test_admin_stats_and_users(admin_api, user_api):
    _make(user_api, "heart")
    stats = admin_api.get("/api/admin/stats").get_json()["data"]
    assert stats["users"]["total"] == 2 and stats["predictions"]["by_disease"]["heart"] == 1
    users = admin_api.get("/api/admin/users").get_json()["data"]["items"]
    assert "password_hash" not in str(users)
    alice = next(u for u in users if u["email"] == "alice@example.com")
    assert alice["prediction_count"] == 1


def test_admin_can_deactivate_user_but_not_self(admin_api, user_api):
    users = admin_api.get("/api/admin/users").get_json()["data"]["items"]
    alice = next(u for u in users if u["email"] == "alice@example.com")
    admin = next(u for u in users if u["email"] == "admin@example.com")
    r = admin_api.patch(f"/api/admin/users/{alice['id']}", {"is_active": False})
    assert r.status_code == 200 and r.get_json()["data"]["user"]["is_active"] is False
    assert user_api.get("/api/auth/me").status_code == 401
    assert admin_api.patch(f"/api/admin/users/{admin['id']}", {"role": "user"}).status_code == 403
    assert admin_api.patch("/api/admin/users/9999", {"is_active": True}).status_code == 404
    assert admin_api.patch(f"/api/admin/users/{alice['id']}", {"role": "superuser"}).status_code == 400


# ---------- admin access to all patients' assessments ----------

def test_admin_sees_all_patients_assessments(admin_api, user_api, other_api):
    a1 = _make(user_api, "heart"); _make(user_api, "kidney"); b1 = _make(other_api, "liver")
    data = admin_api.get("/api/admin/predictions").get_json()["data"]
    assert data["total"] == 3
    assert {i["patient"]["email"] for i in data["items"]} == {"alice@example.com", "bob@example.com"}
    assert data["items"][0]["id"] == b1  # newest first
    # filters
    assert admin_api.get("/api/admin/predictions?disease=heart").get_json()["data"]["total"] == 1
    assert admin_api.get("/api/admin/predictions?q=bob").get_json()["data"]["total"] == 1
    alice_id = data["items"][-1]["patient"]["id"]
    assert admin_api.get(f"/api/admin/predictions?user_id={alice_id}").get_json()["data"]["total"] == 2
    assert admin_api.get("/api/admin/predictions?risk=BAD").status_code == 400
    # detail and report of another user's assessment
    d = admin_api.get(f"/api/admin/predictions/{a1}").get_json()["data"]
    assert d["patient"]["email"] == "alice@example.com" and d["input_data"]["chol"] == 286
    rep = admin_api.get(f"/api/admin/reports/{a1}").get_json()["data"]
    assert rep["generated_for"]["email"] == "alice@example.com"
    assert admin_api.get("/api/admin/predictions/99999").status_code == 404
    u = admin_api.get(f"/api/admin/users/{alice_id}").get_json()["data"]
    assert u["prediction_count"] == 2 and u["by_disease"]["kidney"] == 1


def test_patients_cannot_use_admin_endpoints(user_api, other_api):
    pid = _make(other_api)
    for url in ["/api/admin/predictions", f"/api/admin/predictions/{pid}", f"/api/admin/reports/{pid}", "/api/admin/users/1"]:
        assert user_api.get(url).status_code == 403, url


def test_admin_seeded_from_configuration(make_app):
    from app import ensure_admin
    from app.models import User
    from tests.conftest import Api
    app = make_app()
    with app.app_context():
        assert ensure_admin("Admin@Gmail.com", "admin@123", "Admin") == "created"
        assert ensure_admin("admin@gmail.com", "other-pass-1") == "exists"
        assert User.query.filter_by(email="admin@gmail.com").one().role == "admin"
    a = Api(app.test_client())
    assert a.login("admin@gmail.com", "admin@123").get_json()["data"]["user"]["role"] == "admin"
    assert a.get("/api/admin/predictions").status_code == 200


def test_ensure_admin_promotes_existing_user(app, user_api):
    from app import ensure_admin
    from app.models import User
    with app.app_context():
        assert ensure_admin("alice@example.com", "ignored-123") == "promoted"
        assert User.query.filter_by(email="alice@example.com").one().role == "admin"
    assert user_api.login().status_code == 200  # password unchanged


def test_admin_cannot_use_patient_features(admin_api):
    from tests.conftest import SAMPLES
    r = admin_api.post("/api/predict/heart", {"features": SAMPLES["heart"]})
    assert r.status_code == 403
    for url in ["/api/history", "/api/history/summary", "/api/history/1", "/api/reports/1"]:
        assert admin_api.get(url).status_code == 403, url
    assert admin_api.c.post("/api/ocr/extract", headers=admin_api._headers()).status_code == 403


def test_admin_disease_analytics(admin_api, user_api, other_api):
    _make(user_api, "heart"); _make(user_api, "heart"); _make(other_api, "heart"); _make(other_api, "liver")
    a = admin_api.get("/api/admin/analytics").get_json()["data"]
    h = a["diseases"]["heart"]
    assert h["total"] == 3 and h["patients"] == 2 and h["positive"] == 3 and h["positive_rate"] == 1.0
    assert sum(h["by_risk"].values()) == 3 and 0 < h["avg_probability"] <= 1
    assert a["diseases"]["kidney"]["total"] == 0 and a["diseases"]["kidney"]["avg_probability"] is None
    assert len(a["timeline"]) == 30 and a["timeline"][-1]["heart"] == 3
    assert a["high_risk_patients"][0]["high_count"] >= 1
    patients = admin_api.get("/api/admin/users?role=user").get_json()["data"]["items"]
    assert {u["email"] for u in patients} == {"alice@example.com", "bob@example.com"}
