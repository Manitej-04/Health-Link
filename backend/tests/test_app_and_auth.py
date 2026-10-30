from app.extensions import db
from app.models import User


# ---------- startup / infrastructure ----------

def test_app_starts_and_health_reports_models(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["success"] is True
    assert body["data"]["database"] == "ok"
    assert set(body["data"]["models"]) == {"heart", "diabetes", "kidney", "liver"}


def test_database_tables_created(app):
    with app.app_context():
        tables = set(db.inspect(db.engine).get_table_names())
    assert {"users", "predictions", "token_blocklist"} <= tables


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"


def test_unknown_route_returns_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "not_found"


def test_wrong_method_returns_json_405(client):
    r = client.get("/api/auth/login")
    assert r.status_code == 405
    assert r.get_json()["success"] is False


def test_unhandled_errors_hide_internals(app):
    @app.get("/api/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    r = app.test_client().get("/api/boom")
    assert r.status_code == 500
    assert "secret internal detail" not in r.get_data(as_text=True)
    assert r.get_json()["error"]["code"] == "internal_error"


def test_cors_allows_only_configured_origin(client):
    ok = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"
    bad = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in bad.headers


# ---------- registration ----------

def test_register_success_sets_httponly_cookie(api, app):
    r = api.register()
    assert r.status_code == 201
    user = r.get_json()["data"]["user"]
    assert user["email"] == "alice@example.com" and user["role"] == "user"
    assert "password" not in str(r.get_json()) and "hash" not in str(r.get_json())
    set_cookies = r.headers.getlist("Set-Cookie")
    access = next(c for c in set_cookies if c.startswith("access_token_cookie="))
    assert "HttpOnly" in access
    with app.app_context():
        stored = User.query.filter_by(email="alice@example.com").one()
        assert stored.password_hash != "Password123" and stored.password_hash.startswith("$2")


def test_register_duplicate_email_case_insensitive(api):
    assert api.register().status_code == 201
    r = api.register(email="ALICE@example.com")
    assert r.status_code == 409
    assert r.get_json()["error"]["code"] == "email_taken"


def test_register_rejects_weak_password_and_bad_email(api):
    r = api.register(password="short")
    assert r.status_code == 400 and "password" in r.get_json()["error"]["details"]
    r = api.register(password="lettersonly")
    assert r.status_code == 400
    r = api.register(email="not-an-email")
    assert r.status_code == 400 and "email" in r.get_json()["error"]["details"]


def test_register_rejects_non_json(client):
    r = client.post("/api/auth/register", data="x", content_type="text/plain")
    assert r.status_code == 400


# ---------- login / session ----------

def test_login_success_and_me(api):
    api.register()
    api.c.delete_cookie("access_token_cookie", path="/api/")
    r = api.login()
    assert r.status_code == 200
    me = api.get("/api/auth/me")
    assert me.status_code == 200 and me.get_json()["data"]["user"]["name"] == "Alice Example"


def test_login_wrong_password_and_unknown_user(api):
    api.register()
    r = api.login(password="WrongPass999")
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "invalid_credentials"
    r = api.login(email="nobody@example.com")
    assert r.status_code == 401 and r.get_json()["error"]["message"] == "Incorrect email or password."


def test_protected_endpoints_require_auth(client):
    for method, url in [("get", "/api/auth/me"), ("get", "/api/history"), ("post", "/api/predict/heart"),
                        ("get", "/api/reports/1"), ("post", "/api/ocr/extract"), ("get", "/api/admin/stats")]:
        r = getattr(client, method)(url)
        assert r.status_code == 401, url


def test_csrf_token_required_for_state_changing_requests(user_api):
    r = user_api.c.post("/api/predict/heart", json={"features": {}})  # no X-CSRF-TOKEN header
    assert r.status_code == 401
    assert r.get_json()["error"]["code"] == "csrf_failed"


def test_logout_revokes_token(user_api):
    cookie = user_api.c.get_cookie("access_token_cookie", path="/api/").value
    assert user_api.post("/api/auth/logout").status_code == 200
    # Re-using the old token after logout must fail.
    user_api.c.set_cookie("access_token_cookie", cookie, path="/api/")
    r = user_api.get("/api/auth/me")
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    client.set_cookie("access_token_cookie", "not.a.jwt", path="/api/")
    assert client.get("/api/auth/me").status_code == 401


def test_login_rate_limited(make_app):
    from tests.conftest import Api
    app = make_app(LOGIN_RATE_LIMIT=3)
    a = Api(app.test_client())
    a.register()
    codes = [a.login(password="WrongPass999").status_code for _ in range(4)]
    assert codes[:3] == [401, 401, 401] and codes[3] == 429


def test_deactivated_user_cannot_login_or_use_session(user_api, app):
    with app.app_context():
        u = User.query.filter_by(email="alice@example.com").one()
        u.is_active = False
        db.session.commit()
    assert user_api.get("/api/auth/me").status_code == 401
    assert user_api.login().status_code == 403


def test_profile_update_and_password_change(user_api):
    r = user_api.patch("/api/auth/me", {"name": "Alice Renamed"})
    assert r.status_code == 200 and r.get_json()["data"]["user"]["name"] == "Alice Renamed"
    r = user_api.post("/api/auth/change-password", {"current_password": "wrong", "new_password": "NewPass456"})
    assert r.status_code == 400
    r = user_api.post("/api/auth/change-password", {"current_password": "Password123", "new_password": "NewPass456"})
    assert r.status_code == 200
    assert user_api.login(password="NewPass456").status_code == 200
