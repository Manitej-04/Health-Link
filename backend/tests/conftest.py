import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app import create_app  # noqa: E402
from app.extensions import bcrypt, db  # noqa: E402
from app.models import User  # noqa: E402

ARTIFACTS = BACKEND / "ml" / "artifacts"

# Real records taken from the public datasets (not invented values).
SAMPLES = {
    # Cleveland row 2: 67,1,4,160,286,0,2,108,1,1.5,2,3,3 -> num=2 (disease)
    "heart": {"age": 67, "sex": 1, "cp": 4, "trestbps": 160, "chol": 286, "fbs": 0, "restecg": 2,
              "thalach": 108, "exang": 1, "oldpeak": 1.5, "slope": 2, "ca": 3, "thal": 3},
    # Pima row 1: 6,148,72,35,0,33.6,0.627,50 -> outcome 1 (insulin 0 = missing)
    "diabetes": {"pregnancies": 6, "glucose": 148, "blood_pressure": 72, "skin_thickness": 35, "insulin": None,
                 "bmi": 33.6, "dpf": 0.627, "age": 50},
    # UCI CKD id 0 (rbc, sod, pot missing in the source record)
    "kidney": {"age": 48, "bp": 80, "sg": 1.02, "al": 1, "su": 0, "rbc": None, "pc": 0, "pcc": 0, "ba": 0,
               "bgr": 121, "bu": 36, "sc": 1.2, "sod": None, "pot": None, "hemo": 15.4, "pcv": 44, "wc": 7800,
               "rc": 5.2, "htn": 1, "dm": 1, "cad": 0, "appet": 0, "pe": 0, "ane": 0},
    # ILPD row 1: 65,Female,0.7,0.1,187,16,18,6.8,3.3,0.9 -> liver patient
    "liver": {"age": 65, "gender": 0, "total_bilirubin": 0.7, "direct_bilirubin": 0.1, "alkaline_phosphatase": 187,
              "alt": 16, "ast": 18, "total_proteins": 6.8, "albumin": 3.3, "ag_ratio": 0.9},
}


@pytest.fixture
def make_app():
    apps = []

    def _make(**overrides):
        app = create_app("testing", overrides)
        apps.append(app)
        return app

    yield _make
    for app in apps:
        with app.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def isolated_artifacts(tmp_path):
    """A private copy of the trained artifacts that a test may corrupt."""
    dest = tmp_path / "artifacts"
    shutil.copytree(ARTIFACTS, dest)
    return dest


class Api:
    """Thin helper around the Flask test client that handles the CSRF header."""

    def __init__(self, client):
        self.c = client

    def _headers(self):
        cookie = self.c.get_cookie("csrf_access_token")
        return {"X-CSRF-TOKEN": cookie.value} if cookie else {}

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None, **kw):
        return self.c.post(url, json=json, headers={**self._headers(), **kw.pop("headers", {})}, **kw)

    def patch(self, url, json=None, **kw):
        return self.c.patch(url, json=json, headers={**self._headers(), **kw.pop("headers", {})}, **kw)

    def delete(self, url, **kw):
        return self.c.delete(url, headers={**self._headers(), **kw.pop("headers", {})}, **kw)

    def register(self, email="alice@example.com", password="Password123", name="Alice Example"):
        return self.post("/api/auth/register", {"name": name, "email": email, "password": password})

    def login(self, email="alice@example.com", password="Password123"):
        return self.post("/api/auth/login", {"email": email, "password": password})


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def user_api(api):
    assert api.register().status_code == 201
    return api


@pytest.fixture
def other_api(app):
    a = Api(app.test_client())
    assert a.register(email="bob@example.com", name="Bob Example").status_code == 201
    return a


@pytest.fixture
def admin_api(app):
    with app.app_context():
        db.session.add(User(name="Admin", email="admin@example.com", role="admin",
                            password_hash=bcrypt.generate_password_hash("AdminPass123").decode()))
        db.session.commit()
    a = Api(app.test_client())
    assert a.login("admin@example.com", "AdminPass123").status_code == 200
    return a
