---
phase: 10
plan: "01"
subsystem: backend-config
tags: [system_config, orm, alembic, admin-api, redis-cache, pydantic, endpoint-validation]
dependency_graph:
  requires: [database, redis, admin-router, cyperf_service]
  provides: [system_config-table, GET /admin/config/cyperf-endpoint, POST /admin/config/cyperf-endpoint]
  affects: [admin.py, cyperf_service.py, models/__init__.py]
tech_stack:
  added: [httpx (for connectivity validation)]
  patterns: [ORM class-method upsert, Redis cache-aside, Pydantic v2 field_validator, async graceful degradation]
key_files:
  created:
    - backend/db/system_config.py
    - backend/migrations/versions/006_add_system_config.py
    - backend/tests/test_admin_config.py
  modified:
    - backend/db/__init__.py
    - backend/models/__init__.py
    - backend/routes/admin.py
    - backend/services/cyperf_service.py
decisions:
  - "system_config as generic key-value table (not cyperf_endpoint-specific column) — extensible for future admin config keys without new migrations"
  - "validate_endpoint_connectivity returns (bool, str) tuple — caller decides HTTP status code, function stays pure and testable"
  - "SSL verification disabled for CyPerf connectivity check — CyPerf ships with self-signed certificates (pre-existing pattern in CyperfService)"
  - "GET endpoint returns is_valid=False — validation status is only set by POST; GET only reports current value, not connectivity"
  - "Redis cache failure is non-fatal for both GET and POST — DB is source of truth; cache miss causes one extra DB round-trip"
  - "models/ package (not models.py) is the active models source — models.py is a legacy artifact shadowed by the package directory"
metrics:
  duration: "~6 minutes (02:53:02Z to 02:58:39Z)"
  completed: "2026-02-27"
  tasks_completed: 4
  tests_added: 17
  files_modified: 7
---

# Phase 10 Plan 01: Backend Configuration Storage Summary

**One-liner:** PostgreSQL system_config key-value store with Redis cache-aside and GET/POST admin endpoints for dynamic CyPerf Controller endpoint management.

---

## What Was Built

### Task 1: SystemConfig ORM Model + Alembic Migration 006

Created `/backend/db/system_config.py` — a generic key-value config table:

- **Table**: `system_config` with `id` (PK), `config_key` (VARCHAR 100, UNIQUE), `config_value` (TEXT), `created_at`, `updated_at`
- **Index** + `UniqueConstraint` on `config_key` for O(log n) lookups
- **`get_value(session, key, default=None)`**: async class method returning stored value or default
- **`set_value(session, key, value)`**: atomic upsert — creates if absent, updates if present

Migration `006_add_system_config.py` chains from revision `005`, compatible with both SQLite (dev) and PostgreSQL (prod).

### Task 2: Pydantic Request/Response Models

Added `EndpointConfigRequest` and `EndpointConfigResponse` to `models/__init__.py`:

- **`EndpointConfigRequest`**: `field_validator` strips `http://`/`https://` prefix, rejects empty values, rejects `@` (credential injection), validates against hostname/IP character set (`[a-zA-Z0-9._\-\[\]:]`)
- **`EndpointConfigResponse`**: `endpoint` (str), `is_valid` (bool), `last_validated_at` (datetime|None), `error_message` (str|None)

Key discovery: `models/` package (not `models.py`) is the active models module — the standalone file is shadowed by the package directory.

### Task 3: GET /admin/config/cyperf-endpoint

Resolution waterfall with graceful degradation at each level:

1. **Redis cache** (`cyperf:endpoint` key) — served with `is_valid=True`
2. **Database** (`system_config` WHERE `config_key='cyperf_endpoint'`) — populates cache on hit
3. **Environment variable** `CYPERF_CONTROLLER_IP` — backwards-compatible fallback
4. **Empty string** — degraded response with `is_valid=False`, HTTP 200 always returned

Added `validate_endpoint_connectivity(endpoint: str) -> tuple[bool, str]` to `cyperf_service.py`:
- httpx GET to `https://{endpoint}/api/v2/profiles`, timeout=5s, `verify=False`
- Classifies: `ConnectTimeout`, `ReadTimeout`, `ConnectError` (DNS/refused), unexpected errors
- Never raises — returns `(bool, error_message_string)`

### Task 4: POST /admin/config/cyperf-endpoint

Atomic validate-then-persist flow:

1. Pydantic validates request format (HTTP 422 on bad input)
2. `validate_endpoint_connectivity()` checks reachability (HTTP 400 if unreachable)
3. `SystemConfig.set_value()` upserts to database (HTTP 500 only here, if DB fails post-validation)
4. Redis: `delete(key)` then `set(key, value, ex=3600)` — invalidate-before-set prevents stale reads
5. Returns `EndpointConfigResponse(is_valid=True, last_validated_at=<UTC now>)`

Redis cache failure in POST is non-fatal (logged as warning, DB remains authoritative).

---

## Test Suite

`/backend/tests/test_admin_config.py` — **17 tests, all passing**

| Category | Tests |
|----------|-------|
| GET: cache hit fast-path | 1 |
| GET: DB fallback (+ cache population) | 1 |
| GET: env-var fallback | 1 |
| GET: Redis unavailable → DB | 1 |
| GET: empty degraded response | 1 |
| GET: response shape (all fields) | 1 |
| POST: success (save + cache + timestamp) | 1 |
| POST: HTTP 400 on connectivity failure | 1 |
| POST: HTTP 422 on empty endpoint | 1 |
| POST: HTTP 422 on credentials in endpoint | 1 |
| POST: https:// prefix stripped | 1 |
| POST: Redis unavailable → DB still saved | 1 |
| POST: last_validated_at is UTC ISO timestamp | 1 |
| ORM: get_value None default | 1 |
| ORM: get_value custom default | 1 |
| ORM: set_value create | 1 |
| ORM: set_value upsert | 1 |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] models/ package shadows models.py**

- **Found during:** Task 2 (ImportError: cannot import name 'EndpointConfigRequest' from 'models')
- **Issue:** The plan specified adding models to `models.py`. The project has a `models/` package directory that Python prefers over `models.py`. All existing model imports resolve to `models/__init__.py`.
- **Fix:** Added `EndpointConfigRequest` and `EndpointConfigResponse` to `models/__init__.py` instead. Reverted stray edits to `models.py` to keep it consistent with its current legacy state.
- **Files modified:** `backend/models/__init__.py`
- **Commit:** e583e29

**2. [Rule 2 - Missing Critical] GET endpoint imports datetime but doesn't use timezone constant**

- **Found during:** Task 3/4 commit — ruff auto-fixed `datetime(tz=timezone.utc)` to `datetime(tz=UTC)` (Python 3.11+ style) and removed unused `datetime, timezone` import pair
- **Fix:** Applied ruff changes (auto-fix accepted) — `from datetime import UTC, datetime`
- **Commits:** da99d53, 9ecb5c9

---

## Architecture Invariants Maintained

- Admin endpoints never return 5xx (except POST HTTP 500 if DB fails after validation passed — this is documented and intentional)
- Credentials never logged — only endpoint hostnames appear in logs
- Redis cache failure is non-fatal at every callsite (GET and POST)
- Backwards compatibility: `CYPERF_CONTROLLER_IP` env var continues to work if `system_config` table is empty
- SSL verification disabled for CyPerf (self-signed cert, pre-existing pattern)

---

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| `backend/db/system_config.py` exists | FOUND |
| `backend/migrations/versions/006_add_system_config.py` exists | FOUND |
| `backend/tests/test_admin_config.py` exists | FOUND |
| `backend/db/__init__.py` modified | FOUND |
| `backend/models/__init__.py` modified | FOUND |
| `backend/routes/admin.py` modified | FOUND |
| `backend/services/cyperf_service.py` modified | FOUND |
| commit fdd5ec6 (Task 1) | FOUND |
| commit e583e29 (Task 2) | FOUND |
| commit da99d53 (Task 3) | FOUND |
| commit 9ecb5c9 (Task 4) | FOUND |
| GET /admin/config/cyperf-endpoint registered | FOUND |
| POST /admin/config/cyperf-endpoint registered | FOUND |
| 17 tests passing | CONFIRMED |
