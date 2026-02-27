# E2E Test Plan: Dynamic CyPerf Endpoint Configuration

## Overview

This document defines the end-to-end test scenarios for Phase 10: Dynamic CyPerf
Endpoint Configuration. It covers user-visible workflows from the frontend UI through
to backend API and database state.

## Prerequisites

- Backend running on http://localhost:8000 (or via `./start.sh`)
- Frontend running on http://localhost:5174
- Redis available (optional — graceful degradation tested in Scenario 5)
- Empty or test-seeded database

---

## Test Scenarios

### Scenario 1: Happy Path — Configure Endpoint and Sync

**Steps:**

1. Open frontend app at http://localhost:5174
2. Observe the navbar: "Sync Data" button should be disabled (no endpoint configured)
3. Observe the gear icon (Settings) is highlighted with accent colour (endpoint not configured)
4. Click the gear Settings button in the top-right navbar
5. Verify the SettingsPanel modal opens with title "CyPerf Controller Settings"
6. Enter `cyperf.example.com` in the "Controller Endpoint" input field
7. Click "Save & Validate"

**Expected:**
- Loading toast: "Validating endpoint..."
- Backend calls `POST /admin/config/cyperf-endpoint` with `{ endpoint: "cyperf.example.com" }`
- If connectivity check passes: success toast "Endpoint validated and saved!"
- Modal closes automatically after ~1 second
- Settings gear icon loses accent highlight (endpoint now configured)
- "Sync Data" button becomes enabled

8. Click "Sync Data"

**Expected:**
- Loading toast: "Starting CyPerf sync..."
- Backend calls `POST /admin/sync-cyperf-now`
- Button shows "Syncing..." with spinner, disabled
- If sync queues: toast updates to "Sync queued — polling for completion..."
- When sync completes: success toast shows CVE count e.g. "Sync completed — 3421 CVEs extracted"
- Button returns to "Sync Data" (idle)
- Timestamp "Last: HH:MM" appears next to button

9. Refresh page (F5)

**Expected:**
- Endpoint config persists (fetched from DB)
- "Sync Data" button enabled
- Last sync timestamp visible

---

### Scenario 2: Endpoint Validation Failure

**Steps:**

1. Click Settings gear button
2. Enter `unreachable.example.com`
3. Click "Save & Validate"

**Expected:**
- Loading toast: "Validating endpoint..."
- Backend rejects with HTTP 400 (connection timeout/unreachable)
- Error toast displays specific reason (e.g., "Endpoint unreachable (connection timeout after 5 seconds)")
- Inline error banner appears in modal with the same message
- Modal stays open (not auto-closed)
- "Save & Validate" button re-enabled for retry

4. Clear input and type a valid reachable endpoint
5. Click "Save & Validate"

**Expected:** Success path as in Scenario 1.

---

### Scenario 3: Empty Endpoint State

**Steps:**

1. Ensure no endpoint is configured (fresh database, no env var)
2. Observe the navbar
3. Click "Sync Data" button (should be disabled — verify button is not clickable)

**Expected:**
- Button has `disabled` attribute
- `aria-label` reads "Sync Data (endpoint not configured)"
- `title` tooltip reads "Configure CyPerf endpoint in settings before syncing"

4. Verify Settings gear icon is highlighted in accent colour
5. Click Settings gear button
6. Leave endpoint input empty

**Expected:**
- "Save & Validate" button is disabled
- Cannot submit empty endpoint

---

### Scenario 4: Concurrent Sync Attempts

**Steps:**

1. Configure valid endpoint (Scenario 1 steps 1-7)
2. Click "Sync Data"
3. While the button shows "Syncing..." (loading state), attempt to click "Sync Data" again

**Expected:**
- Button is disabled during loading (pointer-events-none + opacity-50)
- Second click does not fire an additional POST request
- Only one sync job created (verify in backend logs)
- No data corruption — sync completes normally

---

### Scenario 5: Network Error During Sync

**Steps:**

1. Configure valid endpoint
2. Stop the backend server (or use browser DevTools > Network > Offline)
3. Click "Sync Data"

**Expected:**
- Error toast: "Sync failed: Network Error" (or equivalent)
- Button returns to idle state after ~5 seconds
- Inline error message appears below button
- App remains functional (navigation still works)

4. Restore network connection
5. Click "Sync Data" again

**Expected:** Sync proceeds normally.

---

### Scenario 6: Redis Unavailable (Graceful Degradation)

**Steps:**

1. Stop the Redis container (`docker stop redis` or equivalent)
2. Reload the frontend
3. Configure endpoint via Settings panel

**Expected:**
- POST /admin/config/cyperf-endpoint still returns 200 (DB save succeeds)
- Success toast displays normally
- App logs a Redis warning (check backend logs: "Redis not running")

4. GET /admin/config/cyperf-endpoint

**Expected:**
- Returns endpoint from DB (Redis miss → DB lookup succeeds)
- No visible degradation to the user

---

## API Curl Examples

```bash
# Get current configured endpoint
curl -X GET http://localhost:8000/admin/config/cyperf-endpoint | jq .

# Expected response (endpoint not configured):
# {
#   "endpoint": "",
#   "is_valid": false,
#   "last_validated_at": null,
#   "error_message": null
# }

# Set and validate endpoint
curl -X POST http://localhost:8000/admin/config/cyperf-endpoint \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "cyperf.example.com"}' | jq .

# Expected response (success):
# {
#   "endpoint": "cyperf.example.com",
#   "is_valid": true,
#   "last_validated_at": "2026-02-27T03:00:00Z",
#   "error_message": null
# }

# Trigger immediate sync
curl -X POST http://localhost:8000/admin/sync-cyperf-now | jq .

# Expected response (scheduler path):
# {
#   "status": "sync_queued",
#   "job_id": "manual_sync_<uuid>",
#   "endpoint": "cyperf.example.com",
#   "message": "Manual sync queued using endpoint: cyperf.example.com"
# }

# Expected response (direct fallback path):
# {
#   "status": "sync_completed",
#   "job_id": null,
#   "endpoint": "cyperf.example.com",
#   "message": "Sync completed directly (scheduler unavailable)"
# }

# Check sync status
curl -X GET http://localhost:8000/admin/sync-status | jq .

# Expected response (after sync):
# {
#   "status": "success",
#   "last_successful_sync": "2026-02-27T03:01:23Z",
#   "last_attempted_sync": "2026-02-27T03:01:23Z",
#   "profiles_synced": 247,
#   "cves_extracted": 3421,
#   "error_message": null,
#   "next_scheduled_sync": "2026-02-28T02:00:00Z"
# }
```

---

## Accessibility Checklist

- [ ] All buttons have text labels (not icons only): "Sync Data", "Save & Validate", "Cancel"
- [ ] Settings gear button has `aria-label="Open CyPerf endpoint settings"`
- [ ] "Sync Data" button has descriptive `aria-label` in each state (idle, loading, disabled)
- [ ] Error messages use `role="alert"` with `aria-live="polite"` for screen reader announcements
- [ ] Success banners use `role="status"` for screen reader announcements
- [ ] Modal content is keyboard accessible (Tab navigation inside dialog)
- [ ] Radix Dialog handles focus trapping automatically (Tab cycles within dialog)
- [ ] Error/success messages use both colour and icon (not colour-only)
- [ ] Focus visible on all interactive elements (focus-visible ring)
- [ ] Settings gear button has descriptive `title` tooltip
- [ ] Toasts are dismissable (sonner closeButton=true)

---

## Security Checklist

- [ ] No credentials (passwords, API keys) stored in frontend code or localStorage
- [ ] Endpoint input stripped of http:// prefix and validated against hostname/IP charset
- [ ] Embedded credentials (user:pass@host) rejected by Pydantic validator (HTTP 422)
- [ ] Error messages from backend do not expose file paths or stack traces
- [ ] API error detail messages are user-friendly (e.g., "connection timeout", not Python traceback)
- [ ] All CyPerf API calls made from backend only (never from browser)
- [ ] Connectivity check uses HTTPS with 5-second timeout (no infinite hang)
- [ ] SQL injection: SQLAlchemy ORM + parameterised queries throughout (no raw SQL)
- [ ] XSS: React JSX escapes all user-provided strings by default
- [ ] No sensitive data in console logs (backend logs hostname only, never credentials)

---

## Performance Checklist

- [ ] SyncButton initial render < 50ms (no blocking I/O on mount)
- [ ] SettingsPanel modal opens < 200ms (Radix Dialog animation)
- [ ] POST /admin/config/cyperf-endpoint responds < 6s (5s connectivity timeout + overhead)
- [ ] POST /admin/sync-cyperf-now responds < 200ms (scheduler queue, not sync itself)
- [ ] Sync status poll interval is 2 seconds (not lower — avoids API spam)
- [ ] Endpoint config refresh interval is 30 seconds (low frequency — config rarely changes)
- [ ] Redis cache TTL is 1 hour — reduces DB queries for high-traffic scenarios
- [ ] No memory leaks: verify useSyncPolling interval cleared on component unmount
- [ ] No duplicate polling: useSyncStatus (background) and useSyncPolling (post-trigger) are separate hooks

---

## Backwards Compatibility Checklist

- [ ] CYPERF_CONTROLLER_IP env var still works as endpoint source if system_config is empty
- [ ] Scheduled sync (02:00 UTC daily) continues to run when no manual trigger is active
- [ ] Existing browse/search pages unaffected by Phase 10 changes
- [ ] AI CVEs page unaffected
- [ ] Contact form unaffected
- [ ] useSyncStatus hook (used by StatusBar and StaleDataWarning) still works independently

---

## Test Results

| Scenario | Status | Notes |
|----------|--------|-------|
| 1. Happy path: configure + sync | — | Pending manual execution |
| 2. Endpoint validation failure | — | Pending manual execution |
| 3. Empty endpoint state | — | Pending manual execution |
| 4. Concurrent sync prevention | — | Pending manual execution |
| 5. Network error handling | — | Pending manual execution |
| 6. Redis unavailable (degraded) | — | Pending manual execution |

Update this table after manual testing. Replace `—` with `PASS` or `FAIL (details)`.
