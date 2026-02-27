# Phase 10: Dynamic Keysight CyPerf Endpoint + Navbar Sync Button

**Status:** Planning
**Goal:** Users can dynamically configure the Keysight CyPerf endpoint and manually trigger data sync from the UI.

---

## Requirements Met

1. **ND-01**: Users can set Keysight CyPerf endpoint (DNS or IP) via frontend UI
2. **ND-02**: Endpoint configuration persists across session restarts
3. **ND-03**: Navbar displays current endpoint + "Sync Data" button
4. **ND-04**: Clicking "Sync Data" triggers immediate CVE/Apps sync with backend
5. **ND-05**: UI shows sync status (loading, success, error) with timestamp of last sync
6. **ND-06**: Backend API validates endpoint connectivity before accepting it
7. **ND-07**: System gracefully handles unreachable endpoints (existing behavior maintained)

---

## Architecture Decisions

### Data Storage
- **Backend**: Store endpoint in PostgreSQL `system_config` table (new)
- **Cache**: Redis key `cyperf:endpoint` for fast lookups
- **Fallback**: Environment variable `CYPERF_CONTROLLER_IP` if config table is empty

### API Design
- `GET /admin/config/cyperf-endpoint` — Get current endpoint
- `POST /admin/config/cyperf-endpoint` — Update endpoint + validate
- `POST /admin/sync-cyperf-now` — Trigger immediate sync (returns job ID)
- `GET /admin/sync-status` — Get last sync result + endpoint

### Frontend Components
- **Settings Panel** (modal in navbar) — Endpoint input field + save button
- **Sync Button** (navbar) — Displays status + last sync timestamp
- **Toast Notifications** — Show validation errors, sync progress, success/failure

---

## Implementation Waves

### Wave 1: Backend Configuration Storage (1 task)
- [ ] **10-01**: Create `system_config` table; implement config GET/POST endpoints with validation

### Wave 2: Sync Triggering (1 task)
- [ ] **10-02**: Add `POST /admin/sync-cyperf-now` endpoint; return job status; verify existing scheduler still works

### Wave 3: Frontend UI (2 tasks)
- [ ] **10-03**: Build navbar Sync button + settings panel component
- [ ] **10-04**: Integrate with backend; handle validation errors, show real-time sync status

### Wave 4: Testing & Polish (1 task)
- [ ] **10-05**: Integration tests, endpoint validation logic, graceful degradation tests

---

## Success Criteria

✓ User can enter a DNS name or IP in the navbar settings panel
✓ Endpoint is validated (via test connection to `/api/v2/profiles`)
✓ Endpoint persists across browser sessions and server restarts
✓ Clicking "Sync Data" button shows loading indicator and triggers sync
✓ Last sync timestamp displayed in navbar
✓ If endpoint is invalid, UI shows error without crashing
✓ Existing scheduled sync continues to work with new endpoint
✓ No sensitive data (credentials) exposed in frontend code

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| User enters malformed endpoint | Validate format before saving; test connection to Cyperf API |
| Sync fails mid-operation | Keep previous sync data; show error toast; allow retry |
| Multiple sync jobs queued | Prevent concurrent syncs (check job status before queuing) |
| Endpoint changed while sync running | Running sync completes with old endpoint; next sync uses new one |
| Credentials stored in localStorage | Never store credentials; use server-side session only |

---

## Rollback Plan

- If endpoint validation fails: revert to environment variable `CYPERF_CONTROLLER_IP`
- If config table migration fails: skip table creation; use env vars only
- If sync endpoint breaks: disable "Sync Data" button; keep scheduled sync working

---

## Related Issues

- Prevents technical debt: endpoint is now configurable without rebuilding/redeploying
- Future: Multi-controller support (store multiple endpoints in config table)
- Future: Endpoint health monitoring dashboard
