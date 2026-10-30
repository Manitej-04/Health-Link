# API documentation

Base URL: `http://127.0.0.1:5000/api` (proxied as `/api` by the Vite dev server).

## Conventions

* JSON in, JSON out. Every response uses one envelope:

```json
{ "success": true,  "data": { ... } }
{ "success": false, "error": { "code": "validation_error", "message": "…", "details": { "field": "…" } } }
```

* **Authentication**: a JWT in the HttpOnly cookie `access_token_cookie` (path `/api/`, SameSite=Lax, 2-hour expiry by default), set by register/login.
* **CSRF**: state-changing requests (POST/PATCH/DELETE) to authenticated endpoints must send header `X-CSRF-TOKEN` equal to the readable cookie `csrf_access_token`.
* Common status codes: 200, 201, 400 validation, 401 not signed in / expired / CSRF, 403 forbidden, 404 not found (also used for other users' records), 409 duplicate email, 413 upload too large, 415 unsupported file, 422 unreadable file, 429 rate limited, 503 model unavailable / OCR engine missing, 500 generic (no internals exposed).

## Public

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{status, database, models: {heart: "available", …}}` |
| GET | `/models` | Module list: status, reasons, `probability_supported`, algorithm, held-out metrics, and the full **input schema** (`features[]` with `name,label,type,unit,min,max,options,required,help`); plus `risk_bands` and `disclaimer`. The frontend builds every form from this. |

## Authentication

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{name, email, password}` | 201 + session cookie. Password ≥ 8 chars with a letter and a digit. Email unique (case-insensitive). |
| POST | `/auth/login` | `{email, password}` | 401 `invalid_credentials`; 403 `account_disabled`; 429 after 5 attempts / 5 min per IP+email. |
| POST | `/auth/logout` | — | Revokes the token (blocklist) and clears cookies. |
| GET | `/auth/me` | — | `{user}` |
| PATCH | `/auth/me` | `{name}` | Update display name. |
| POST | `/auth/change-password` | `{current_password, new_password}` | |

`user` objects: `{id, name, email, role, is_active, created_at, last_login_at}` — never the password hash.

## Predictions

### POST `/predict/<disease>`  (`heart` | `diabetes` | `kidney` | `liver`)

```json
{ "features": { "glucose": 148, "insulin": null, ... }, "source": "manual" }
```

* All required fields must be present and within range; unknown fields are rejected.
* Optional fields (`required: false` in the schema) may be `null` = explicitly "not available".
* `source`: `manual` or `ocr` (recorded for the report).

Response 201 (probability-supported module):

```json
{
  "id": 12, "created_at": "2026-10-30T15:56:01Z",
  "disease": "diabetes", "disease_name": "Diabetes",
  "predicted_class": 1, "predicted_label": "Diabetes indicated",
  "probability": 0.6831, "risk_category": "MODERATE",
  "risk_bands": [{"category": "LOW", "range": "below 30%", "min": 0, "max": 0.3}, …],
  "model_status": "available", "model_algorithm": "Logistic Regression", "model_version": "2026-10-30T15:41:37+00:00",
  "explanation": "…", "factors": [{"feature": "glucose", "label": "…", "direction": "increases", "weight": 1.21}],
  "not_provided": [{"feature": "insulin", "label": "2-hour serum insulin"}],
  "imputation_notice": "…", "disclaimer": "…"
}
```

For a class-only module (`kidney`): `probability: null`, `risk_category: null`,
`risk_unavailable_reason`, `experimental_notice`, `factors: null`.

Errors: 400 `validation_error` with per-field `details`; 404 `unknown_disease`;
503 `model_unavailable` (artifact missing/corrupt/incompatible).

## History and reports (owner-only)

| Method | Path | Description |
|---|---|---|
| GET | `/history?page=1&per_page=10&disease=heart` | Paginated summaries, newest first. `per_page` ≤ 50. |
| GET | `/history/summary` | Totals by module, counts by module × risk band, 5 most recent, probability trend. |
| GET | `/history/<id>` | Full record incl. stored inputs. |
| DELETE | `/history/<id>` | Delete one record. |
| GET | `/reports/<id>` | Printable report data: report id, user, labelled inputs with units, result, risk bands, model info, disclaimer. |

Records belonging to another user return **404** (indistinguishable from non-existent).

Patient-only endpoints (`/predict/*`, `/history*`, `/reports/<id>`, `/ocr/extract`) return **403** for administrator accounts.

## OCR

### POST `/ocr/extract` (multipart/form-data)

Fields: `disease`, `file` (PNG, JPEG or PDF ≤ 5 MB; first 3 PDF pages).

```json
{
  "disease": "liver",
  "extracted": [{"field": "total_bilirubin", "label": "Total bilirubin", "value": 1.2, "valid": true,
                 "error": null, "source_line": "Total Bilirubin 1.2 mg/dL"}],
  "missing": [{"field": "albumin", "label": "Albumin", "required": true}],
  "characters_recognised": 241, "text_preview": "…"
}
```

Only values on the same line as a recognised label are returned. OCR never runs
a prediction; the client must submit reviewed values to `/predict/<disease>`.

## Admin (role `admin`)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/analytics` | Per disease: total assessments, distinct patients, predicted-positive count and rate, average probability, counts per risk band; 30-day daily timeline; top patients by number of HIGH results. |
| GET | `/admin/stats` | User counts, prediction counts by module and band, model status. |
| GET | `/admin/users` | Users with prediction counts (no password hashes). |
| GET | `/admin/users/<id>` | One patient: profile, counts by module and risk band. |
| PATCH | `/admin/users/<id>` | `{is_active?, role?}`; cannot modify yourself. |
| GET | `/admin/predictions?page&per_page&user_id&disease&risk&q` | **All patients' assessments**, newest first, each with `patient {id,name,email}`. `risk` = LOW/MODERATE/HIGH/NONE; `q` searches name/email. |
| GET | `/admin/predictions/<id>` | Any assessment in full (inputs, result) plus patient. |
| GET | `/admin/reports/<id>` | Printable report data for any assessment. |

Create an admin with `flask create-admin`, or set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`: the account is created at startup if it does not exist (an existing account with that email is promoted; its password is not changed).
