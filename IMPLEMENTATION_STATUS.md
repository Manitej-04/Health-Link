# Implementation status

Last updated: 2026-10-30. Built and verified in a Linux workspace (Python 3.13.18, Node 22.23.4, scikit-learn 1.9.1, Tesseract 5.3.4).

## Phase log

| Phase | Result | Verification |
|---|---|---|
| 1. Project folder and scaffold | Done | Fresh `Health-Link-Final/`; no existing project touched |
| 2. Flask backend, database, authentication | Done | pytest auth/app suites |
| 3. Datasets and ML pipelines | Done — UCI host blocked from build environment; datasets taken from public mirrors and verified against UCI's published statistics (`backend/ml/datasets/SOURCES.md`) | `test_ml.py`; `reports/model_evaluation.md` |
| 4. Prediction services and standardised results | Done | `test_predictions.py` |
| 5. History and reports | Done | `test_history_reports_admin.py` |
| 6. React frontend, integrated | Done | Vitest; `npm run build`; browser end-to-end run |
| 7. OCR and dashboard | Done | `test_ocr.py` (real Tesseract on generated PNG and PDF); browser OCR → form → prediction |
| 8. Security review, tests, docs | Done | `docs/SECURITY.md`; full suites below |

## Test results (actual)

* `cd backend && python -m pytest` → **113 passed**, 0 skipped, ~25 s
* `python scripts/generate_sample_reports.py` → 16 reports × (PNG + PDF): every input read correctly by OCR in all 32 files; bands as listed in README
* Browser check: OCR upload of sample reports (kidney PDF, heart PNG, liver PDF, diabetes PNG) → fully pre-filled form → results Moderate 45.4%, High 92.8%, Moderate 37.7%, Low 7.0%
* `cd frontend && npm test` → **7 passed**
* `cd frontend && npm run build` → success (code-split; largest chunk 356 kB / 103 kB gzip, the charting library)
* `python backend/scripts/smoke_test.py` against the running server → health 200, register 201, four predictions 201, history total 4, logout then `/me` 401
* Browser end-to-end (Playwright, Chromium) through the Vite proxy: register → dashboard → client validation (13 errors on empty heart form) → heart, diabetes (optional field marked unavailable), kidney (experimental, class only), OCR upload → review → pre-filled liver form → result; result page reload from history; history; printable report (screen and print media); model page; mobile 390 px views; logout and protected-route redirect. Screenshots: `reports/screenshots/`.

## Acceptance criteria

| Criterion | Status | Notes |
|---|---|---|
| Separate new folder `Health-Link-Final` | COMPLETED | |
| Working Flask backend | COMPLETED | |
| Working React frontend | COMPLETED | |
| Working database | COMPLETED | SQLite default; Flask-Migrate initial migration verified with `flask db upgrade`; MySQL via `DATABASE_URL` (configuration only, not run against a MySQL server) |
| Secure authentication | COMPLETED | bcrypt, HttpOnly JWT cookie, CSRF, revocation, rate limit |
| Four independently assessed disease modules | COMPLETED | All four available; kidney carries documented data caveats |
| Genuine model inference | COMPLETED | Test asserts API probability equals the artifact's `predict_proba` |
| Defensible probability output where supported | COMPLETED | Sigmoid calibration inside training split; held-out ECE/Brier criteria met by all four |
| Consistent LOW/MODERATE/HIGH presentation where justified | COMPLETED | Shared backend service + shared `RiskResult` component |
| Prediction history | COMPLETED | Pagination, filter, delete, summary |
| Ownership protection | COMPLETED | Server-side, 404 for others' records; tested |
| Printable reports | COMPLETED | Print stylesheet; "Print or save as PDF" |
| OCR functionality | COMPLETED | PNG/JPEG/PDF; labelled values only; user review required |
| Responsive UI | COMPLETED | Verified at 1366 px and 390 px |
| Automated tests | COMPLETED | 101 backend + 7 frontend |
| Complete documentation | COMPLETED | README, docs/*, SOURCES.md, model report |
| Verified local startup instructions | COMPLETED (Linux) | Commands verified here on Linux; Windows/macOS commands documented but not executed in this environment |

## Change log

* 2026-10-30 (update 2): Kidney module now available — integrity findings shown as data caveats instead of downgrading it. OCR now reads categorical fields (chest pain type, ECG, urine findings, yes/no history, …), "Nil"/"None" results and common O/0 confusions; median blur removed (it erased decimal points). Added `sample_reports/` and its generator.

* 2026-10-30 (update 3): Admin can view all patients' assessments, per-patient history, any result and printable report (`/api/admin/predictions*`, `/api/admin/reports/<id>`, `/api/admin/users/<id>`; Administration page tabs Overview / Patients / All assessments). Admin account can be seeded from `ADMIN_EMAIL`/`ADMIN_PASSWORD`. Backend tests: 111 passed. Browser check: two patients, four OCR assessments, admin sees all four, filters one patient's history, opens result and report.

* 2026-10-30 (update 4): Separate administrator area. Admins land on `/admin` with their own navigation (Overview, Patients, Patient reports, Disease analysis, Model performance, Profile) and are redirected away from patient pages; the API rejects admins on patient-only endpoints (predict, own history/reports, OCR) with 403. New `GET /api/admin/analytics` (per-disease totals, patients, positive rate, average probability, risk bands, 30-day timeline, high-risk patients). Backend tests: 113 passed.

## Known limitations / blockers

* **Official UCI download host was blocked** in the build environment (HTTP 403 from the network proxy). Mirrors were used and verified; see `SOURCES.md` for swapping in official files.
* **Model artifacts are tied to scikit-learn 1.9.1.** On another version the app refuses to load them (by design) — run `python -m ml.training.train` once after installing requirements. Retraining with a different library version can shift metrics slightly; heart's ECE (0.097) is close to the 0.10 threshold, so on some versions heart may switch to class-only output. The app and docs report whatever your run produces.
* Liver model: specificity 0.15 at the 0.5 threshold (accuracy equals the majority baseline); documented prominently.
* Google Fonts (Public Sans) were not reachable from the build environment; the UI falls back to system fonts offline and loads Public Sans when online.
* Not clinically validated. See `docs/ML_METHODOLOGY.md` §10 and `docs/SECURITY.md` residual risks.

## Next steps (optional enhancements)

* External validation data; fairness analysis by sex and age.
* Refresh tokens and password reset by email.
* Redis-backed rate limiting and a production WSGI deployment guide.
