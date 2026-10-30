# Security review

Scope: the Flask API, the React client and the local deployment described in the README.
This is a prototype review, not a penetration test.

| Area | Implementation | Verified by |
|---|---|---|
| Password storage | bcrypt (Flask-Bcrypt, per-hash salt). Plaintext never stored or logged. | `test_register_success_sets_httponly_cookie` |
| Password policy | ≥ 8 chars, letter + digit, max 128 (server and client). | `test_register_rejects_weak_password_and_bad_email` |
| Authentication | JWT (Flask-JWT-Extended) in an **HttpOnly** cookie scoped to `/api/`, SameSite=Lax, `Secure` in production; 2-hour expiry. Not stored in localStorage, so not readable by injected scripts. | auth tests |
| CSRF | Double-submit token: `csrf_access_token` cookie must be echoed in `X-CSRF-TOKEN` on every state-changing request. | `test_csrf_token_required_for_state_changing_requests` |
| Logout / revocation | Token `jti` written to a blocklist table; reuse after logout → 401. Deactivated users' tokens are rejected on every request. | `test_logout_revokes_token`, `test_deactivated_user_cannot_login_or_use_session` |
| Brute force | Login limited to 5 attempts per IP+email per 5 minutes (in-memory, per process). Identical message and bcrypt timing for unknown emails to avoid account enumeration. | `test_login_rate_limited` |
| Authorization / ownership | Every patient history/report/delete query filters by `user_id = current_user.id`; another user's record yields 404. Admin endpoints (`/api/admin/*`) require role `admin`, checked on the server for every request; admins can read every patient's assessments and reports (read-only — they cannot edit or delete them) and cannot change their own role/status. | `test_users_cannot_access_each_others_records`, `test_patients_cannot_use_admin_endpoints`, admin tests |
| Input validation | Marshmallow for auth/profile/admin; schema-driven validation for every feature (type, range, allowed options, unknown-field rejection, NaN/Infinity/bool rejection). Client validation is a convenience only. | `test_validation_and_risk.py` |
| SQL injection | SQLAlchemy ORM with bound parameters only; no string-built SQL. | code review |
| CORS | Restricted to `CORS_ORIGINS` (default the Vite dev origins) with credentials. | `test_cors_allows_only_configured_origin` |
| Security headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, API `Content-Security-Policy: default-src 'none'`, `Cache-Control: no-store`. | `test_security_headers_present` |
| Secrets | Read from `backend/.env` (git-ignored). `.env.example` has placeholders only. Production refuses to start without real secrets; development generates ephemeral random ones with a warning. | `config.finalize_secrets` |
| Error handling | All errors return the JSON envelope; unhandled exceptions are logged server-side and return a generic 500 with no stack trace. | `test_unhandled_errors_hide_internals` |
| Uploads | Size cap (`MAX_CONTENT_LENGTH`, 5 MB → 413); extension allow-list **and** magic-byte check must agree (415); Pillow decompression-bomb limit; PDF limited to 3 pages; files processed **in memory** — nothing written to disk, so no temp-file cleanup is needed. | `test_ocr.py` |
| Model artifacts | `joblib` unpickling can execute code, so each artifact's SHA-256 is stored in `metadata.json` and verified before loading; mismatched, corrupt or version-incompatible artifacts are refused and the module marked unavailable. | `test_corrupt_artifact_fails_integrity_check` and related |
| Logging | Logs record user ids and model status, never passwords, tokens or medical inputs. | code review |
| Medical safety | Disclaimer on every page, result and report; probabilities only when calibration criteria pass; experimental module clearly labelled. | UI + tests |

## Known residual risks / production hardening

* `ADMIN_PASSWORD` in `.env` is plaintext. It is hashed when the account is created; remove the line (or change the password from the Profile page) after the first start, and use a strong password outside a demo.
* Admin access to patient data is not audit-logged.

* The rate limiter is per process; use Flask-Limiter with Redis for multi-instance deployments.
* `python run.py` uses Flask's development server. For a real deployment use a WSGI server (e.g. `waitress-serve --call app:create_app` with `FLASK_ENV_NAME=production`), HTTPS, and `JWT_COOKIE_SECURE=true`.
* No refresh tokens: users sign in again after the access token expires (2 h).
* No email verification or password-reset flow.
* Medical inputs are stored unencrypted in the database; protect the database file/server accordingly.
* The model artifact checksum protects against corruption and casual tampering, but an attacker with write access to the artifact folder could also rewrite `metadata.json`; keep that folder read-only in deployment.
