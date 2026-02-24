# Phase 04.1 Plan 01 Summary: Backend Email Service + FastAPI Endpoint

**Executed:** 2026-02-24
**Status:** Complete
**Commits:** 4 atomic commits tagged (04.1-01)

---

## What Was Built

### `backend/config.py` — SMTP settings extension
- Added 6 new fields to `Settings`: `smtp_server`, `smtp_port`, `smtp_username`, `smtp_password`, `smtp_from_email`, `smtp_recipient_email`
- Defaults: server=`mail.keysight.com`, port=587, from/recipient emails pre-set to Keysight addresses
- Credentials (`smtp_username`, `smtp_password`) default to empty string — not hard crashes — so app starts without them
- `__init__` guard: logs a WARNING if either credential is absent; does NOT crash or block startup
- No live SMTP probe at startup (per plan spec — avoids blocking)

### `backend/services/email_service.py` — Pure email module (new)
- `SMTPConfig` dataclass: typed container for all SMTP connection parameters
- `render_email_subject(context, cve_id) -> str`: maps `"discuss"` → `"Customer Interest: {cve_id} Discussion"`, `"feature_request"` → `"Feature Request: {cve_id}"`, any unknown value → `"CVE Inquiry: {cve_id}"` with WARNING log
- `render_email_body(...)` → clean plain-text body with customer info block, CVE details block, context label, and Cyperf Tracker footer
- `send_contact_email(to_email, subject, body, smtp_config, timeout=10)`: STARTTLS via `smtplib.SMTP`; `ssl.create_default_context()` (cert validation always on); 10s TCP timeout; structured error logging on `SMTPAuthenticationError`, `SMTPException`, and base `Exception`; password never logged
- Zero FastAPI dependencies — fully unit-testable in isolation

### `backend/routes/contact.py` — Contact form router (new)
- `ContactFormRequest` Pydantic model: all fields validated (CVE ID pattern `^CVE-\d{4}-\d{1,7}$`, `EmailStr`, `Literal["discuss","feature_request"]`, min/max_length string guards, `strip_whitespace=True`)
- `ContactFormResponse`: `success`, `message`, `preview` fields
- `_get_smtp_config(settings)` dependency: builds `SMTPConfig` from injected `Settings`
- `_send_email_background(...)`: fire-and-forget wrapper; catches all exceptions and logs without re-raising (background task contract)
- `POST /contact/submit` endpoint: renders subject + body synchronously, queues send via `BackgroundTasks`, logs CVE ID + context + email (NOT name/company — PII minimization), returns `ContactFormResponse` immediately
- `APIRouter(prefix="/contact", tags=["contact"])`

### `backend/main.py` — Router registration
- Added `from routes.contact import router as contact_router`
- Added `app.include_router(contact_router)`

### `.env.example` — SMTP stub variables
- Added 6 SMTP env var stubs under `# EMAIL SERVICE (Phase 4.1 - Sales Funnel)` section

### `backend/requirements.txt` — New dependency
- Added `pydantic[email]==2.6.0` (required for `EmailStr` field type)

---

## Verification Results

All checks passed against the running Docker stack (`cyperf_api_dev`):

| Check | Expected | Actual |
|-------|----------|--------|
| `/contact/submit` in OpenAPI paths | Yes | Yes |
| Valid payload → HTTP 200 + preview | 200 + JSON body | PASS |
| `NOT-A-CVE` cve_id → HTTP 422 | 422 | PASS |
| Invalid email → HTTP 422 | 422 | PASS |
| `render_email_subject("discuss", ...)` assertion | Pass | PASS |
| `render_email_subject("feature_request", ...)` assertion | Pass | PASS |
| `render_email_body(...)` content assertions | Pass | PASS |

---

## Notable Issues

1. **email-validator missing from requirements.txt** — `EmailStr` in Pydantic 2 requires the `email-validator` package. Added `pydantic[email]` to `requirements.txt`. Discovered during import verification of `routes/contact.py`.
2. **Pre-commit ruff auto-fix** — Ruff reformatted the import block in `contact.py` (multi-line import for `email_service` functions) on first commit attempt. Re-staged after auto-fix; second commit passed cleanly.
3. **Python 3.14 / SQLAlchemy incompatibility in local environment** — Running `uvicorn` via system Python 3.14 fails due to SQLAlchemy assertion error on `TypingOnly` subclass. Not introduced by this plan; pre-existing. All verification executed against the Docker container where Python 3.12 is used.

---

## Architecture Notes

- The endpoint is fully non-blocking: HTTP 200 is returned before the SMTP connection is attempted. Delivery failures only appear in server logs.
- SMTP credentials are injected via `Depends(get_settings)` → `_get_smtp_config` — no module-level globals, mockable in tests.
- The `_send_email_background` wrapper absorbs all exceptions from `send_contact_email` to prevent crashing the ASGI background task worker. The underlying `send_contact_email` re-raises so the caller can decide; this design keeps both functions independently testable.
- Password is excluded from all log statements across every code path.
