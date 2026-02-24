# Phase 04.1 Sales Funnel — Summary

---

# Plan 01 Summary: Backend Email Service + FastAPI Endpoint

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

---

---

# Plan 02 Summary: Contact Form Sidebar Component

**Executed:** 2026-02-23
**Status:** Complete
**Commits:** 5 atomic commits tagged (04.1-02)

---

## What Was Built

### `frontend/package.json` — New dependencies
- `react-hook-form@^7.71.2` — form state and validation orchestration
- `@hookform/resolvers@^5.2.2` — bridges Zod schemas to react-hook-form (supports both Zod v3 and v4)
- `zod@^4.3.6` — schema declaration and client-side validation

### `frontend/src/types/api.ts` — Extended with contact form types
- `ContactContext` string literal union: `'discuss' | 'feature_request'`
- `ContactFormRequest`: all 9 fields (first_name, last_name, company, email, cve_id, context, testable, cvss_score, attack_profiles)
- `ContactFormResponse`: `success: boolean`, `message: string`, `preview: string`
- Appended below existing types without modifying them

### `frontend/src/hooks/useContactForm.ts` — API integration hook (new)
- `submitForm(data: ContactFormRequest) → Promise<ContactFormResponse>`: POST to `/api/contact/submit` with 15s timeout
- `isSubmitting` boolean: true during axios call, false on resolution or rejection
- `error: string | null`: populated from `err.response.data.detail` when available; generic message fallback
- `reset()`: clears error state for retry scenarios
- Uses typed `unknown` catch clause (strict TypeScript — no `any`)
- Fully decoupled from component tree — no JSX, no context; mockable in tests

### `frontend/src/components/contact/ConfirmDialog.tsx` — Pre-form confirmation (new)
- Uses `@radix-ui/react-dialog` primitives directly (no new shadcn component created)
- Shows CVE ID + context label before user commits to sharing contact info
- Accessible: Radix-managed focus trap, Escape key → `onCancel()`, `onOpenChange` → `onCancel()`
- `autoFocus` on Continue button for keyboard navigation
- Dark theme: `bg-luxury-bg`, `border-luxury-border`, `text-luxury-accent` (Keysight Red)

### `frontend/src/components/contact/ContactFormSidebar.tsx` — Main sidebar (new)
- State machine: `idle | confirming | form | submitting | success | error`
  - `idle`: Sheet closed, no DOM rendered
  - `confirming`: `ConfirmDialog` shown; Sheet not yet visible
  - `form`/`submitting`: 4-field React Hook Form with inline Zod validation errors
  - `success`: CheckCircle2 icon + "Email sent" message + email preview in monospace `<pre>`
- Zod schema validates `first_name`, `last_name`, `company`, `email` before any network call
- Sheet implemented as Radix Dialog with right-slide animation (`slide-in-from-right`)
- Width: `w-full` on mobile, `sm:w-[420px]` on desktop
- Submit button disabled during `isSubmitting`; shows "Sending…" label
- API error shown inline on form; state stays at `form` for retry (no data loss)
- `onClose` resets form + hook state + response — clean on every open/close cycle
- Read-only context badge: "Regarding: CVE-XXXX-XXXX — Let's Discuss / Request Feature"

---

## Verification Results

| Check | Expected | Actual |
|-------|----------|--------|
| `npm run build` no TypeScript errors | 0 errors | PASS |
| `npx tsc --noEmit` clean | 0 errors | PASS |
| `react-hook-form` in package.json | `^7.71.2` | PASS |
| `zod` in package.json | `^4.3.6` | PASS |
| `@hookform/resolvers` in package.json | `^5.2.2` | PASS |
| `ContactFormSidebar.tsx` accepts all 7 required props | Yes | PASS |
| `ConfirmDialog.tsx` present | Yes | PASS |
| `useContactForm.ts` present | Yes | PASS |
| Zod validates 4 fields before network call | Yes | PASS |
| Build size reasonable (no bloat) | <300kB JS gzip | 81kB gzip |

---

## Notable Decisions

1. **Zod v4 compatibility** — `@hookform/resolvers@5` auto-detects Zod v3 vs v4 via `_zod` property check; no `zod/v3` import required. API is identical (`z.string().min().email()` works in both).
2. **State machine owns isOpen** — `isOpen` prop drives the state machine via `useEffect`; parent does not need to know about internal `confirming` vs `form` vs `success` states. Parent only toggles `isOpen`.
3. **No auto-close timer on success** — User reads the email preview and closes manually. Prevents accidental dismissal before reading confirmation.
4. **Error stays on form** — On API error, state reverts to `form` (not `error` terminal state). User can fix and retry without reopening the sidebar. `apiError` from hook is shown inline.
5. **Typed `unknown` catch** — Plan used `err: any`; replaced with `err: unknown` + type narrowing to satisfy strict TypeScript without disabling rules.

---

## Architecture Notes

- `ContactFormSidebar` is fully self-contained: parent provides `cveId`, `context`, `testable`, `cvssScore`, `attackProfiles`, `isOpen`, `onClose`. No page-level state required.
- The hook (`useContactForm`) is decoupled from the component. It can be tested in isolation without rendering JSX.
- Confirmation dialog and sidebar sheet are separate Radix Dialog roots — they do not nest. This avoids focus trap conflicts.
- The component uses `React.useEffect` with `isOpen` as the only dependency to avoid stale closure issues with form/hook refs.

---

---

# Plan 03 Summary: Integrate Buttons + Sidebar into Search and Browse Pages

**Executed:** 2026-02-23
**Status:** Complete
**Commits:** 3 atomic commits tagged (04.1-03)

---

## What Was Built

### `frontend/src/pages/SearchPage.tsx` — CVE detail card with action buttons
- Added `contactSidebarOpen: boolean` and `contactContext: ContactContext` state at component top level
- Added `openSidebar(ctx: ContactContext)` helper: sets context then opens the sidebar
- Injected an action row at the bottom of the `{cveResult && (...)}` detail card (after Cyperf Test Profiles section):
  - `testable === true`: solid emerald "Let's Discuss" button (`bg-emerald-700 hover:bg-emerald-600`)
  - `testable === false`: outlined "Request Feature" button (`border-luxury-accent/40 text-luxury-accent`)
- Neither button renders until `cveResult` is populated (guard already provided by the existing `{cveResult && (...)}` block)
- Rendered `<ContactFormSidebar>` as a sibling to the detail card block, also guarded by `{cveResult && (...)}` — receives `cveId`, `testable`, `context`, `cvssScore`, `attackProfiles` from live result
- Imported `ContactContext` from `../../types/api` and `ContactFormSidebar` from `../components/contact/ContactFormSidebar`

### `frontend/src/components/shared/DataTable.tsx` — Optional row action column
- Extended `DataTableProps` with two optional fields:
  - `onRowAction?: (cve: CVEResponse) => void` — callback invoked on button click with the full CVE object
  - `rowActionLabel?: string` — button label; defaults to `"Let's Discuss"` when not provided
- Added conditional `<th>` in `<thead>`: renders only when `onRowAction` is defined
- Added conditional `<td>` in each `<tbody>` row: renders only when `onRowAction` is defined
- All existing callers (`SearchPage`) that omit `onRowAction` are completely unaffected — no column rendered, no type errors

### `frontend/src/pages/BrowsePage.tsx` — Per-row engagement action + sidebar
- Added `contactSidebarOpen: boolean` and `selectedCVE: CVEResponse | null` state
- Added `handleRowAction(cve: CVEResponse)` handler: sets `selectedCVE` and opens sidebar
- Passed `onRowAction={handleRowAction}` and `rowActionLabel="Let's Discuss"` to `<DataTable>`
- Rendered `<ContactFormSidebar>` conditionally on `selectedCVE !== null`:
  - `onClose` resets both `contactSidebarOpen` (false) and `selectedCVE` (null) — prevents stale data if user opens a second CVE without a full remount
  - `context="discuss"` (hardcoded: Browse only shows testable CVEs)
- Imported `ContactFormSidebar` from `../components/contact/ContactFormSidebar`

---

## Verification Results

| Check | Expected | Actual |
|-------|----------|--------|
| `npm run build` no TypeScript errors | 0 errors | PASS |
| `tsc` clean (implicit via build) | 0 errors | PASS |
| SearchPage testable CVE: "Let's Discuss" renders | Yes | Code confirmed |
| SearchPage non-testable CVE: "Request Feature" renders | Yes | Code confirmed |
| Neither button before search result loads | Yes | Guarded by `{cveResult && ...}` |
| BrowsePage "Action" column renders with "Let's Discuss" | Yes | Code confirmed |
| DataTable without onRowAction: no Action column | Yes | Conditional render |
| Sidebar context="discuss" in Search + Browse | Yes | Both paths verified |
| Sidebar context="feature_request" in Search (non-testable) | Yes | `openSidebar('feature_request')` |
| selectedCVE reset on sidebar close in BrowsePage | Yes | onClose handler |
| Build size acceptable | <300kB gzip | 130kB gzip (no change) |

---

## Notable Decisions

1. **SearchPage sidebar guarded by `cveResult`** — The `<ContactFormSidebar>` is rendered inside `{cveResult && (...)}` rather than always mounted. This avoids passing empty/null prop values and prevents the Radix Dialog from being mounted in the DOM before it is needed.
2. **BrowsePage `selectedCVE` reset in onClose** — Setting `selectedCVE = null` on close prevents stale CVE data from persisting between sidebar opens. If the user clicks a second row before the sidebar fully unmounts, the next `setSelectedCVE` call triggers a fresh render of the sidebar with correct props.
3. **DataTable backward-compat** — All new props are optional with `?`. No default parameter values were used; instead, runtime `onRowAction &&` guards prevent any render of the new column. This avoids TypeScript requiring default values for callers.
4. **`rowActionLabel` default in JSX** — The fallback `rowActionLabel ?? "Let's Discuss"` is applied inline in JSX rather than as a destructured default. Both approaches are equivalent; the inline approach is marginally more explicit at the usage site.

---

## Architecture Notes

- The SearchPage button placement is at the bottom of the detail card, separated from content by a `border-t`. This follows the visual hierarchy: scan data first, act last.
- BrowsePage uses `context="discuss"` unconditionally because Browse filters to `testable=true` only. There is no code path in BrowsePage that would produce a non-testable CVE in the table.
- All three entry points pass the full `attackProfiles` array to the sidebar so the backend email always includes Cyperf strike context regardless of which page the user is on.
