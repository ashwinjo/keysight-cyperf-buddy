# Phase 3 Plan 1: Cyperf Integration Setup - Summary

**Plan:** 03-01-PLAN.md
**Phase:** 03 - Cyperf Integration + Sync Engine
**Date Completed:** 2026-02-23
**Status:** Complete (5/5 tasks)

---

## What Was Built

Phase 3 Plan 01 establishes the foundational infrastructure for Cyperf integration and background sync scheduling:

### 1. Dependencies Added
- **apscheduler==3.10.4** — AsyncIO-native background job scheduler for FastAPI
- **cyperf-api-wrapper==1.0.0** — Official Keysight-maintained Cyperf API client SDK

### 2. CyperfService Module (`backend/services/cyperf_service.py`)
Async wrapper around cyperf-api-wrapper with:
- **CyperfService class** — Initializes API client with credentials
- **fetch_attack_profiles()** — Async method to retrieve all profiles from Cyperf Controller
- **extract_cves_from_profiles()** — Synchronous parser to map CVE IDs to profile names
- **sync_cyperf_cves()** — Main orchestrator: fetches → extracts → returns SyncResult
- **SyncResult dataclass** — Captures operation results: profiles_fetched, cves_extracted, optional error message
- **Error classes** — CyperfConnectionError (network failures), CyperfAPIError (API-level failures)

**Key Design Decisions:**
- No credentials logged; only job metadata and CVE counts
- Graceful error handling via SyncResult (no exceptions raised during sync)
- Retry logic deferred to Plan 02 (perform_sync orchestrator)

### 3. APScheduler Setup (`backend/scheduler.py`)
Background job orchestration with:
- **setup_scheduler()** — Initializes AsyncIOScheduler with UTC timezone
- **Cron trigger** — Runs daily at **02:00 UTC** (off-peak time)
- **Jitter** — ±5 minutes random jitter (prevents thundering herd in multi-instance deployments)
- **sync_cyperf_job()** — Stub job function called on schedule (expanded in Plan 02)
- **trigger_cyperf_sync_now()** — Manual trigger function (used by POST /admin/sync-cyperf in Plan 02)
- **Misfire grace time** — 600 seconds (10 min) — job still runs if up to 10min late

**Job Lifecycle:**
- Startup: scheduler.start() attaches to FastAPI lifespan (Plan 02)
- Execution: job calls sync_cyperf_job on schedule or manual trigger
- Shutdown: scheduler.shutdown(wait=True) waits for jobs to complete gracefully

### 4. Configuration (`backend/config.py`)
- Added `cyperf_sync_interval_hours: int = 24` (default: daily)
- Logging output: "✓ Cyperf sync interval: 24 hours"
- Future use: Ops can tune sync frequency without redeployment via CYPERF_SYNC_INTERVAL_HOURS env var

### 5. CyperfSupportedCVE Model Enhancement (`backend/db/cyperf_mapping.py`)
- Added `upsert_from_cyperf_data()` classmethod for idempotent insert-or-update
- Updated docstring with sync workflow explanation
- Prepared for Plan 02 database recording via session.merge()

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **APScheduler over alternatives** | Native async support, persistent job store support, proven FastAPI integration pattern |
| **UTC timezone throughout** | Eliminates ambiguity across regions; 02:00 UTC is off-peak for most users |
| **±5min jitter** | Prevents synchronized load spikes in multi-instance deployments; standard practice |
| **No exceptions in sync** | SyncResult captures errors; Plan 02 records them without raising, enabling graceful degradation |
| **Synchronous CVE extraction** | Parsing is CPU-bound, not I/O-bound; async overhead not warranted |
| **Full refresh strategy** | Simpler than delta tracking; handles profile deletions/changes correctly; acceptable performance at 02:00 UTC |
| **Credentials never logged** | Security best practice; logging shows only metrics and job metadata |

---

## Files Created/Modified

| File | Status | Changes |
|------|--------|---------|
| `backend/requirements.txt` | Modified | Added apscheduler, cyperf-api-wrapper |
| `backend/services/cyperf_service.py` | Created | CyperfService, SyncResult, error classes (231 lines) |
| `backend/scheduler.py` | Created | APScheduler setup, job functions, manual trigger (186 lines) |
| `backend/config.py` | Modified | Added cyperf_sync_interval_hours setting + logging |
| `backend/db/cyperf_mapping.py` | Modified | Added upsert_from_cyperf_data() classmethod + docstring |

---

## Dependencies on Plan 02

Plan 01 is **infrastructure-complete but logic-incomplete**:

- **sync_cyperf_job()** is stubbed; Plan 02 wires it to perform_sync() for database recording
- **Scheduler is initialized but not started** in lifespan; Plan 02 adds startup/shutdown in main.py
- **No database recording** yet; Plan 02 adds SyncService with retry logic and graceful degradation
- **No admin endpoints** yet; Plan 02 adds GET /admin/sync-status and POST /admin/sync-cyperf
- **Search endpoint unchanged** from Phase 2; Plan 02 adds testable + attack_profile fields

---

## Test Commands (Plan 01 Verification)

**Syntax check:**
```bash
python3 -m py_compile backend/services/cyperf_service.py
python3 -m py_compile backend/scheduler.py
python3 -m py_compile backend/db/cyperf_mapping.py
```

**Import verification:**
```bash
python3 -c "from backend.services.cyperf_service import CyperfService, SyncResult; print('✓')"
python3 -c "from backend.scheduler import setup_scheduler; print('✓')"
python3 -c "from backend.db.cyperf_mapping import CyperfSupportedCVE; print('✓')"
```

**Dependencies installed (after `pip install -r backend/requirements.txt`):**
```bash
python3 -c "import apscheduler; import cyperf_api_wrapper; print('✓ All deps present')"
```

---

## Commits

| Hash | Message |
|------|---------|
| 8c1a69c | feat(03-01): add APScheduler and CyperfService integration |
| 69905bb | feat(03-01): add config setting and upsert method for CyperfSupportedCVE |

---

## Next: Plan 02

Plan 02 will complete Phase 3 by:
1. Implementing SyncService with retry logic and graceful degradation
2. Adding database recording (SyncMetadata methods)
3. Creating admin endpoints (GET /admin/sync-status, POST /admin/sync-cyperf)
4. Integrating testability into GET /cve/search endpoint
5. Wiring scheduler job to perform_sync() for full sync lifecycle

---

**Deviations from Plan:** None. All tasks executed exactly as specified.

**Status:** Phase 3 Plan 01 complete. Ready for Plan 02 execution.
