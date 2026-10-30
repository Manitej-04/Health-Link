# Health-Link

Health-Link is an educational web application that runs machine-learning models trained on four public clinical datasets — **heart disease, diabetes, chronic kidney disease and liver disease** — and presents each result against a reference-range style scale.

> **Medical disclaimer.** Health-Link is an educational prototype only. Its predictions are not clinically validated and must not be used for diagnosis, treatment decisions, or emergencies. Consult a qualified healthcare professional for medical concerns.

---

## Features

* Registration, sign-in, sign-out, profile and password change (bcrypt, HttpOnly JWT cookie, CSRF protection, login rate limiting).
* Four assessment modules with forms generated from each model's own input schema; server-side validation of every value.
* Calibrated probability, application-defined **LOW / MODERATE / HIGH** band, predicted class, explanation and the inputs that most moved the estimate — in one shared result layout.
* All four modules are available with calibrated probabilities; dataset limitations found by the integrity checks are listed as **data caveats** on the Model performance page (see `docs/ML_METHODOLOGY.md`).
* Private, paginated prediction history; detail view; printable / save-as-PDF report.
* OCR: upload a PNG/JPEG/PDF lab report, review and correct the labelled values found, then continue to the form.
* Dashboard with module status, recent results and a chart of your assessments; model-performance page with real held-out metrics.
* Admin area: **every patient's assessments and history** (search, filter by module/risk, open any result or printable report), patient accounts (activate/deactivate, roles), statistics, model availability.
* 16 sample lab reports (PNG + PDF) in `sample_reports/` covering low, moderate and high results — upload them on **Read a report** for a full demo.
* 113 backend tests, 7 frontend tests, production build verified.

## Technology

| Layer | Stack |
|---|---|
| Frontend | React 19, Vite 8, React Router 7, Axios, React Context, Recharts, Lucide icons, custom CSS |
| Backend | Python 3.10+, Flask 3, Flask-SQLAlchemy / SQLAlchemy 2, Flask-Migrate, Flask-JWT-Extended, Flask-Bcrypt, Flask-CORS, Marshmallow |
| ML | scikit-learn, pandas, NumPy, joblib, Matplotlib |
| OCR | OpenCV, Tesseract OCR, pytesseract, pypdfium2 (PDF) |
| Database | SQLite (default), MySQL optional |
| Tests | pytest, Vitest + React Testing Library |

## Folder structure

```text
Health-Link-Final/
├── backend/
│   ├── app/                 Flask application
│   │   ├── __init__.py      app factory + CLI
│   │   ├── config.py  extensions.py
│   │   ├── models/  routes/  services/  schemas/  utils/  middleware/
│   ├── ml/
│   │   ├── feature_specs.py input schemas (single source of truth)
│   │   ├── datasets/        raw/ + SOURCES.md
│   │   ├── preprocessing/   loaders.py, pipeline.py
│   │   ├── training/        train.py
│   │   ├── evaluation/      metrics.py, integrity.py
│   │   └── artifacts/       <disease>/model.joblib, metadata.json, plots
│   ├── migrations/          Flask-Migrate
│   ├── tests/               pytest suite
│   ├── scripts/smoke_test.py
│   ├── requirements.txt  run.py  pytest.ini  .env.example
├── frontend/
│   ├── public/  index.html  package.json  vite.config.js
│   └── src/  App.jsx main.jsx components/ pages/ context/ services/ utils/ styles/ test/
├── docs/        ARCHITECTURE.md  API_DOCUMENTATION.md  ML_METHODOLOGY.md  SECURITY.md
├── reports/     model_evaluation.md
├── README.md  IMPLEMENTATION_STATUS.md  LICENSE  .gitignore
```

## Prerequisites

* **Python 3.10 or newer** (`python --version`)
* **Node.js 20.19+ or 22.12+** and npm (`node --version`) — required by Vite 8
* **Tesseract OCR** (only for the OCR feature)
  * Windows: install from the UB Mannheim build (https://github.com/UB-Mannheim/tesseract/wiki). If `tesseract` is not on PATH, set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` in `backend/.env`.
  * macOS: `brew install tesseract` · Ubuntu/Debian: `sudo apt install tesseract-ocr`

## Backend setup

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# configuration
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux
# then put two random values in SECRET_KEY and JWT_SECRET_KEY:
python -c "import secrets; print(secrets.token_hex(32))"
```

### Train the models (required once per machine)

The shipped artifacts were built with scikit-learn 1.9.1. Pickled models are only safe to load with the same version, so the server refuses mismatched artifacts and marks those modules unavailable. Retrain locally — it takes about 1–2 minutes:

```bash
python -m ml.training.train          # all four; or: python -m ml.training.train heart
```

This rewrites `ml/artifacts/*` and `reports/model_evaluation.md` with your own run's real metrics.

### Database

Tables are created automatically on first start (SQLite file `backend/instance/healthlink.db`). To manage the schema with migrations instead, set `AUTO_CREATE_TABLES=false` and run:

```bash
flask db upgrade
```

MySQL: `pip install pymysql`, create a database, and set `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/healthlink`.

Create an administrator (optional) — either add to `backend/.env` (created automatically at next start):

```
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=choose-a-password
```

or run `flask create-admin` (prompts for email, name, password). Signing in with it opens the administrator area (Overview, Patients, Patient reports, Disease analysis). Admin accounts review patients' data and do not run assessments themselves.

### Run

```bash
python run.py                 # http://127.0.0.1:5000  (check http://127.0.0.1:5000/api/health)
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

The dev server proxies `/api` to `http://127.0.0.1:5000`, so the session cookie works without cross-site configuration. Production build: `npm run build` (output in `frontend/dist/`).

## Environment configuration (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_ENV_NAME` | development | `production` requires real secrets and secure cookies |
| `SECRET_KEY`, `JWT_SECRET_KEY` | — | random strings; dev falls back to ephemeral values (sessions reset on restart) |
| `DATABASE_URL` | SQLite in `instance/` | any SQLAlchemy URL |
| `AUTO_CREATE_TABLES` | true | false → use `flask db upgrade` |
| `CORS_ORIGINS` | localhost:5173 origins | comma-separated |
| `JWT_ACCESS_MINUTES` | 120 | session length |
| `JWT_COOKIE_SECURE` | false | true when served over HTTPS |
| `MAX_UPLOAD_MB` | 5 | OCR upload limit |
| `LOGIN_RATE_LIMIT` / `LOGIN_RATE_WINDOW_SECONDS` | 5 / 300 | login throttling |
| `RISK_LOW_MAX` / `RISK_MODERATE_MAX` | 0.30 / 0.70 | educational band cut-offs |
| `TESSERACT_CMD` | — | path to tesseract executable if not on PATH |

## Datasets

`backend/ml/datasets/raw/` contains the four public datasets; provenance, verification against UCI's published statistics, checksums, licences and expected formats are in `backend/ml/datasets/SOURCES.md`. To use freshly downloaded official files, place them in the documented format and retrain.

## Model training and evaluation (summary)

Stratified 80/20 split; model selection by repeated 5-fold CV ROC-AUC on the training split among Logistic Regression, Decision Tree, KNN, SVM, Random Forest and Gradient Boosting; sigmoid calibration fitted inside the training split; single held-out evaluation. Shipped run:

| Module | Status | Model | Test ROC-AUC (95% CI) | Accuracy (baseline) | Sensitivity / Specificity | ECE | Probability shown |
|---|---|---|---|---|---|---|---|
| Heart | available | Logistic Regression | 0.958 (0.898–0.996) | 0.869 (0.541) | 0.929 / 0.818 | 0.097 | yes |
| Diabetes | available | Logistic Regression | 0.812 (0.740–0.872) | 0.701 (0.649) | 0.481 / 0.820 | 0.056 | yes |
| Kidney | available (data caveats) | Logistic Regression | 1.000 (optimistic — see caveats) | 0.975 (0.625) | 0.960 / 1.000 | 0.078 | yes |
| Liver | available | Logistic Regression | 0.805 (0.726–0.879) | 0.711 (0.711) | 0.938 / 0.152 | 0.081 | yes |

Full details, eligibility rules and caveats: `docs/ML_METHODOLOGY.md`, `reports/model_evaluation.md`, plots in `backend/ml/artifacts/<disease>/`.

## Prediction workflow

1. Choose a module (**New assessment**) or start from **Read a report**.
2. Fill the form; optional fields can be marked *Not available* (disclosed in the result).
3. The server validates, runs the model and saves the result; you see the shared result view.
4. Open the printable report and use **Print or save as PDF**.

Risk bands (application-defined, educational, not clinical): LOW < 30%, MODERATE 30–70%, HIGH ≥ 70% of the calibrated probability. Shown only for modules whose probabilities passed the calibration criteria.

## OCR usage

**Read a report** → pick the module → upload a PNG, JPEG or PDF (≤ 5 MB). Health-Link reads only numbers that appear next to a recognised label on the same line (e.g. `Total Bilirubin 1.2 mg/dL`). Review the table, correct or untick values, then continue: the form opens with those values highlighted and everything else empty. Nothing is predicted until you submit the form. Files are processed in memory and not stored.

## Sample test reports

`sample_reports/` holds 16 lab-report style documents (each as PNG and PDF): 4 per module. Upload any of them on **Read a report** with the matching module selected; every input is read automatically. `sample_reports/answer_key.csv` lists the expected band and probability for each. Regenerate them with `python scripts/generate_sample_reports.py` (from `backend/`) after retraining.

| Module | Report 01 | Report 02 | Report 03 | Report 04 |
|---|---|---|---|---|
| Heart | Low 7.0% | Moderate 44.6% | High 92.8% | Moderate 62.1% |
| Diabetes | Low 7.0% | Moderate 44.9% | High 92.2% | Moderate 62.1% |
| Kidney | Low 7.0% | Moderate 45.4% | High 93.8% | Moderate 63.0% |
| Liver | Moderate 37.7% (lowest the model gives) | Moderate 45.0% | Moderate 62.1% | High 93.0% |

## API

See `docs/API_DOCUMENTATION.md`. Key endpoints: `/api/auth/*`, `/api/health`, `/api/models`, `/api/predict/<disease>`, `/api/history`, `/api/history/<id>`, `/api/history/summary`, `/api/reports/<id>`, `/api/ocr/extract`, `/api/admin/*`.

## Testing

```bash
cd backend && python -m pytest            # 113 tests (OCR endpoint tests skip if Tesseract is missing)
cd frontend && npm test                   # 7 component/validation tests
cd frontend && npm run build              # production build
python backend/scripts/smoke_test.py      # against a running backend
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| Module shows **Unavailable**: "trained with scikit-learn X" | Run `python -m ml.training.train` in `backend/` with your venv active. |
| "Cannot reach the Health-Link server" | Start the backend (`python run.py`) before the frontend; check port 5000 is free. |
| Signed out after restarting the backend | Set fixed `SECRET_KEY` and `JWT_SECRET_KEY` in `backend/.env`. |
| `csrf_failed` 401 | Use the app through `http://localhost:5173` (the proxy), not by opening the API directly from another origin. |
| OCR returns 503 | Install Tesseract and/or set `TESSERACT_CMD`. |
| `npm run dev` fails on Node version | Install Node 20.19+ or 22.12+. |
| Login says "Too many sign-in attempts" | Wait 5 minutes or restart the backend (limits are in memory). |

## Known limitations

* Not clinically validated; small, narrow, historic datasets; no external validation or fairness analysis.
* Kidney dataset caveats: haemoglobin alone nearly separates the classes and CKD records have far more missing values, so its near-perfect test score is optimistic and unlikely to hold on new patients.
* The liver model never estimates below about 35%, so it cannot produce a LOW result (its training data is 71% positive).
* Liver model's predicted class is close to uninformative (specificity 0.15 at the 0.5 threshold); its calibrated probability is more useful than the class.
* Development server only (`run.py`); see `docs/SECURITY.md` for production hardening.
* OCR depends on image quality and recognises a fixed list of label spellings in English.
* No email verification, password reset or refresh tokens.

## Licence

Code: MIT (see `LICENSE`). Datasets remain under their original terms (see `SOURCES.md`).
