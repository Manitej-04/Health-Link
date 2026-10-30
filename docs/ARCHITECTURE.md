# Architecture

```
 Browser (React 19 + Vite)                        Flask API (Python)                       Storage
 ──────────────────────────                       ───────────────────                      ───────
 pages/ ─► components/ ─► services/api.js ──/api──► routes/ ─► services/ ──────────────► SQLite / MySQL
   AuthContext (session)      axios + CSRF header      auth        validation (schema)     users, predictions,
   ModelsContext (/models)                             predictions prediction_service       token_blocklist
   ToastContext                                         system      risk (shared bands)
                                                        (health,    model_registry ───────► ml/artifacts/*/
                                                         ocr,admin) ocr_service               model.joblib
                                                                                             metadata.json
                     ml/feature_specs.py  ◄── single source of truth for every input schema ──►  ml/training
```

## Backend (`backend/`)

* `app/__init__.py` — application factory: config, extensions, JWT callbacks, error handlers, security headers, blueprints, model registry, CLI (`init-db`, `create-admin`).
* `app/config.py` — environment-driven config classes (development / testing / production).
* `app/models/` — SQLAlchemy models `User`, `Prediction`, `TokenBlocklist`.
* `app/schemas/` — Marshmallow request schemas (auth, profile, admin).
* `app/routes/` — `auth.py`, `predictions.py` (models, predict, history, reports), `system.py` (health, OCR, admin).
* `app/services/`
  * `validation.py` — schema-driven feature validation.
  * `model_registry.py` — loads artifacts once, verifies checksum / scikit-learn version / feature schema, reports availability.
  * `prediction_service.py` — inference and the **standardised result object** used by all four modules.
  * `risk.py` — shared LOW / MODERATE / HIGH classifier.
  * `ocr_service.py` — OpenCV preprocessing + Tesseract + labelled-value parser.
* `app/middleware/` — error envelope, JWT callbacks, security headers, `admin_required`.
* `app/utils/` — response helpers, login rate limiter.
* `ml/` — `feature_specs.py`, `preprocessing/` (loaders, pipeline), `training/train.py`, `evaluation/` (metrics, integrity), `datasets/raw/`, `artifacts/`.
* `migrations/` — Flask-Migrate (Alembic) initial schema.
* `tests/` — pytest suite with an in-memory database and private artifact copies for corruption tests.

## Database

| users | | predictions | |
|---|---|---|---|
| id PK | | id PK | |
| name | | user_id FK → users.id (indexed, cascade delete) | |
| email UNIQUE, indexed | | disease (indexed) | |
| password_hash (bcrypt) | | input_data JSON (validated values) | |
| role (`user`/`admin`) | | not_provided JSON | |
| is_active | | predicted_class, predicted_label | |
| created_at, last_login_at | | probability NULL, risk_category NULL | |
| | | model_status, model_algorithm, model_version | |
| | | factors JSON, source (`manual`/`ocr`), created_at (indexed) | |

`token_blocklist(id, jti UNIQUE, created_at, expires_at)` stores revoked tokens; expired rows are pruned at logout.

## Frontend (`frontend/src/`)

* `main.jsx` — providers: Router → Toast → Auth → Models.
* `App.jsx` — routes; authenticated pages are lazy-loaded and wrapped in `ProtectedRoute` (admin pages additionally check role).
* `services/api.js` — axios instance (`withCredentials`, CSRF header, 401 → session-expired event) and typed API helpers.
* `context/` — `AuthContext` (current user, login/register/logout), `ModelsContext` (schemas, status, bands), `ToastContext`.
* `components/` — `AppShell` (sidebar, mobile drawer, disclaimer), `AssessmentForm` (generated from schema), `RiskResult` + `RiskGauge` (**one result layout for every module**), badges, common states.
* `pages/` — Landing, Login/Register, Dashboard, DiseaseSelect, Assessment (one route per disease: `/assess/heart` …), Result, History, Report (print), OCR, Model performance, Profile, Admin.
* `styles/global.css` — design tokens and all styles, including print rules.

## Request flow: a prediction

1. Assessment page reads the module schema from `ModelsContext` and renders the form.
2. Client validation gives instant feedback; submit is disabled while in flight.
3. `POST /api/predict/<disease>` with CSRF header → JWT check → `validate_features` → `run_prediction` (registry → `predict_proba` → class at 0.5 → risk band if probability is supported) → row saved in one transaction → 201.
4. The client navigates to `/results/<id>` with the response; opening that URL later rebuilds the same view from `GET /api/history/<id>`.
