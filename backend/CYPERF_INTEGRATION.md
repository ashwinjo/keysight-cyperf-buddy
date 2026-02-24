# Cyperf Integration + Sync Engine (Phase 3)

## Architecture Overview

The Cyperf Integration provides a persistent, locally-cached mapping of CVE IDs to Cyperf Attack Profiles. This avoids repeated API calls to the Cyperf Controller and enables efficient querying of testable CVEs.

### Component Stack

```
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Admin Endpoints                                     │
│ • POST /admin/sync-cyperf         (manual trigger)         │
│ • GET /admin/sync-status          (status + history)        │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────v────────────────────────────────────────────┐
│ APScheduler (Background Job Queue)                          │
│ • Runs daily at 02:00 UTC (±5min jitter)                   │
│ • max_instances=1 (prevents concurrent syncs)              │
│ • Retries on failure (3 attempts: 0s, 0s, 5s)              │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────v────────────────────────────────────────────┐
│ SyncService (Orchestration)                                 │
│ • perform_sync() — main entry point                        │
│ • Handles retries, error recovery, database recording      │
│ • Graceful degradation (logs error, retains old data)      │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────v────────────────────────────────────────────┐
│ CyperfService (API Client)                                  │
│ • fetch_attack_profiles() — list all profiles              │
│ • extract_cves_from_profiles() — parse CVEs from metadata  │
│ • sync_cyperf_cves() — orchestrate fetch + extract         │
│ • Uses cyperf-api-wrapper for REST communication           │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────v────────────────────────────────────────────┐
│ Cyperf Controller (52.32.20.150)                            │
│ • RESTful API providing attack profile metadata             │
│ • Credentials: admin / CyPerf&Keysight#1                   │
└─────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. GET /admin/sync-status

**Purpose:** Check Cyperf sync history and current status.

**Response:**
```json
{
  "last_successful_sync": "2025-02-23T08:15:32Z",
  "last_attempted_sync": "2025-02-23T10:15:32Z",
  "sync_status": "success",
  "cverf_profiles_synced": 247,
  "cverf_cves_extracted": 3421,
  "error_message": null,
  "next_scheduled_sync": "2025-02-24T02:00:00Z"
}
```

**Status Values:**
- `"success"` — Last sync completed successfully
- `"failed"` — Last sync attempt failed (error_message will be set)
- `"running"` — Sync currently in progress
- `"never"` — Cyperf has never been synced since startup

**HTTP Status:**
- `200 OK` — Always returns successfully (even on internal errors)

**Notes:**
- `cverf_cves_extracted` is the current count of CVEs in the database (as of last successful sync)
- `error_message` is only set when sync_status is "failed"
- All timestamps are ISO 8601 format with Z (UTC) suffix

---

### 2. POST /admin/sync-cyperf

**Purpose:** Trigger an immediate Cyperf sync outside the normal schedule.

**Request:**
```bash
curl -X POST http://localhost:8000/admin/sync-cyperf
```

**Response (202 Accepted):**
```json
{
  "status": "sync_triggered",
  "message": "Cyperf sync queued for immediate execution"
}
```

**OR (if scheduler not running):**
```json
{
  "status": "sync_completed",
  "message": "Cyperf sync completed immediately"
}
```

**Error Response (500):**
```json
{
  "detail": "Failed to trigger sync: <error details>"
}
```

**Notes:**
- Returns immediately (202 Accepted); sync runs in background
- Check `/admin/sync-status` to monitor progress
- If scheduler is not running, sync executes directly and returns 200 (instead of 202)

---

## Database Schema

### CyperfSupportedCVE Table
```sql
CREATE TABLE cyperf_supported_cves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,

  -- Foreign key to CVEs
  cve_id VARCHAR(20) UNIQUE NOT NULL
    REFERENCES cves(id) ON DELETE CASCADE,

  -- Attack profile details
  attack_profile_name VARCHAR(255) NOT NULL,
  attack_profile_id VARCHAR(100),
  profile_version VARCHAR(50),

  -- Sync tracking
  first_synced DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_synced DATETIME,
  is_deprecated BOOLEAN DEFAULT 0
);

-- Indexes for query performance
CREATE INDEX idx_cyperf_cve ON cyperf_supported_cves(cve_id);
CREATE INDEX idx_cyperf_profile ON cyperf_supported_cves(attack_profile_name);
```

### SyncMetadata Table
```sql
CREATE TABLE sync_metadata (
  id INTEGER PRIMARY KEY AUTOINCREMENT,

  -- Job identification
  job_name VARCHAR(50) UNIQUE NOT NULL,

  -- Execution tracking
  last_run_at DATETIME,
  last_completed_at DATETIME,

  -- Status
  status VARCHAR(20),  -- 'success', 'failed', 'running'
  error_message TEXT,

  -- Results
  profiles_synced INTEGER,

  -- Scheduling
  next_scheduled_run DATETIME,

  -- Metadata
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sync_job ON sync_metadata(job_name);
```

---

## Sync Workflow

### Happy Path: Successful Sync

```
[Scheduled Time or Manual Trigger]
    ↓
[SyncMetadata.record_sync_start()]
    ↓
[Attempt 1: CyperfService.sync_cyperf_cves()]
    ├─ fetch_attack_profiles() → profiles list
    ├─ extract_cves_from_profiles(profiles) → {cve_id: profile_name}
    └─ ✓ Success
    ↓
[Upsert CVE mappings to database]
    ├─ For each cve_id → profile_name:
    │  └─ CyperfSupportedCVE.upsert_from_cyperf_data()
    └─ session.commit()
    ↓
[SyncMetadata.record_sync_complete(success=True)]
    ├─ status = "success"
    ├─ last_completed_at = now
    ├─ next_scheduled_run = now + 24 hours
    └─ session.commit()
    ↓
[Next sync scheduled for 24 hours later]
```

### Error Path: Cyperf Unreachable

```
[Scheduled Time or Manual Trigger]
    ↓
[SyncMetadata.record_sync_start()]
    ↓
[Attempt 1: CyperfService.sync_cyperf_cves()]
    └─ ✗ CyperfConnectionError
    ↓
[Wait 0 seconds, Attempt 2]
    └─ ✗ CyperfConnectionError
    ↓
[Wait 5 seconds, Attempt 3]
    └─ ✗ CyperfConnectionError
    ↓
[SyncMetadata.record_sync_complete(success=False)]
    ├─ status = "failed"
    ├─ error_message = "Connection error: ..."
    ├─ last_completed_at = UNCHANGED (retains last-known-good)
    ├─ profiles_synced = UNCHANGED
    ├─ next_scheduled_run = now + 24 hours
    └─ session.commit()
    ↓
[Circuit breaker check]
    ├─ If 3+ consecutive failures:
    │  └─ Log alert: "Check Cyperf controller availability"
    └─ Else: silent
    ↓
[Next sync scheduled (retries automatically)]
```

### Idempotent Upsert Pattern

Each CVE-to-profile mapping uses SQLAlchemy's `session.merge()` to create or update:

```python
record = CyperfSupportedCVE(
    cve_id="CVE-2024-1234",
    attack_profile_name="Apache-Log4j-RCE",
    attack_profile_id="profile-12345",
    profile_version="2.0",
    last_synced=datetime.utcnow(),
    is_deprecated=False,
)
merged = session.merge(record)
# If record exists: updates last_synced, is_deprecated
# If new: creates with first_synced=now
```

This pattern ensures:
- **No duplicate CVEs** (unique constraint on cve_id)
- **Preserves creation time** (first_synced unchanged on update)
- **Tracks updates** (last_synced updated on each sync)
- **Marks active mappings** (is_deprecated reset to False)

---

## Configuration

### Environment Variables

```bash
# Cyperf Controller
CYPERF_CONTROLLER_IP=52.32.20.150
CYPERF_USERNAME=admin
CYPERF_PASSWORD=CyPerf&Keysight#1

# Sync interval (hours, default 24)
CYPERF_SYNC_INTERVAL_HOURS=24

# Database
DATABASE_URL=sqlite+aiosqlite:///./cyperf_cve.db

# Logging
LOG_LEVEL=INFO

# Environment
ENVIRONMENT=development
```

### Scheduler Settings

**Sync Schedule:** Daily at 02:00 UTC

**Jitter:** ±5 minutes (prevents thundering herd if multiple instances)

**Misfire Grace:** 10 minutes (if job is delayed, it will still run if within 10 min)

**Coalesce:** True (don't run multiple times if delayed)

**Max Instances:** 1 (only one sync at a time)

---

## Cyperf API Wrapper Specification

### Required Interface

The `cyperf-api-wrapper` package must provide:

```python
from cyperf_api_wrapper import CyperfApiClient

class CyperfApiClient:
    def __init__(
        self,
        controller_address: str,
        username: str,
        password: str
    ) -> None:
        """Initialize Cyperf API client with controller credentials."""
        ...

    def get_all_attack_profiles(self) -> List[Dict[str, Any]]:
        """
        Fetch all attack profiles from Cyperf Controller.

        Returns:
            List of attack profile dictionaries. Expected schema:
            [
                {
                    "id": "profile-uuid-1",
                    "name": "Apache-Log4j-RCE",
                    "description": "Tests for Log4j RCE vulnerability",
                    "version": "2.0",
                    "cves": ["CVE-2021-44228", "CVE-2021-44229"],
                    # OR
                    "metadata": {
                        "cves": ["CVE-2021-44228"]
                    }
                },
                ...
            ]

        Raises:
            ConnectionError: If unable to connect to controller
            Exception: If authentication fails (with "401" or "unauthorized")
        """
        ...
```

### Expected Response Schema

**Attack Profile Object:**
```json
{
  "id": "profile-uuid-1",
  "name": "Apache-Log4j-RCE",
  "description": "Tests for Log4j RCE vulnerability",
  "version": "2.0",
  "cves": ["CVE-2021-44228", "CVE-2021-44229"],
  "metadata": {
    "attack_type": "RCE",
    "affected_systems": ["Apache", "Log4j"],
    "severity": "CRITICAL"
  }
}
```

**CVE Extraction Logic:**
The sync service looks for CVEs in this order:
1. `profile["cves"]` — Direct list of CVE strings
2. `profile["metadata"]["cves"]` — CVEs nested in metadata
3. Falls back to empty list if neither found

CVE strings can be:
- Direct string: `"CVE-2021-44228"`
- Dictionary with `id` or `cve_id` key: `{"id": "CVE-2021-44228"}`

---

## Error Handling & Graceful Degradation

### Design Philosophy

**"Never corrupt the database; always retain stale data over no data."**

### Failure Modes

#### 1. Cyperf Controller Unreachable

**What happens:**
- Logs connection error
- Retries 2 more times with backoff (0s, 5s)
- After 3 attempts, marks sync as failed in sync_metadata
- Keeps all previous CVE mappings in database

**User Impact:** None (sync_status shows "failed" but all previous data intact)

**Recovery:** Automatic retry on next scheduled sync

#### 2. Cyperf API Returns Auth Error

**What happens:**
- Raises CyperfAPIError("Authentication failed")
- No retry (credentials won't change)
- Marks sync as failed in sync_metadata
- Logs alert to check credentials

**User Impact:** Sync fails; admin must verify credentials

**Recovery:** Manual sync after fixing .env

#### 3. Database Write Fails

**What happens:**
- Session rolls back (no partial writes)
- Marks sync as failed in sync_metadata
- Retries on next scheduled sync

**User Impact:** None (all data retained)

**Recovery:** Automatic retry; logs database error for investigation

#### 4. Circuit Breaker: 3+ Consecutive Failures

**What happens:**
- After 3rd consecutive failure, logs alert
- "Circuit breaker: 3 consecutive failures. Check Cyperf controller availability."

**User Impact:** Alert in logs; sync_status shows failed

**Recovery:** Admin must investigate Cyperf availability; sync retries automatically

---

## Logging Strategy

### Log Levels

**INFO:**
- Sync started / completed
- Profiles fetched count
- CVEs extracted count
- Sync duration

**WARNING:**
- Failed retry attempt
- Partial data (some CVEs extracted despite errors)
- Circuit breaker triggered

**ERROR:**
- Connection errors
- Auth errors
- Database errors
- All 3 retry attempts failed

### Log Example

```
INFO     Starting Cyperf sync operation...
INFO     Cyperf sync attempt 1/3...
INFO     Initializing Cyperf API client for controller 52.32.20.150
INFO     ✓ Cyperf API client initialized for 52.32.20.150
INFO     Fetching attack profiles from Cyperf Controller...
INFO     ✓ Fetched 247 attack profiles from Cyperf in 2.34s
INFO     Extracting CVEs from 247 attack profiles...
INFO     ✓ Extracted 3421 CVE-to-profile mappings
INFO     ✓ Cyperf sync completed: fetched 247 profiles, extracted 3421 CVEs in 2.45s
INFO     ✓ Upserted 3421 CVE-profile mappings to database
INFO     ✓ Cyperf sync SUCCEEDED: 247 profiles, 3421 CVEs, 2.67s, attempt 1
```

---

## Testing & Troubleshooting

### Manual Sync via API

```bash
# Trigger sync
curl -X POST http://localhost:8000/admin/sync-cyperf

# Response: 202 Accepted (or 200 OK if scheduler not running)
{
  "status": "sync_triggered",
  "message": "Cyperf sync queued for immediate execution"
}

# Check status (wait a few seconds, then check)
curl http://localhost:8000/admin/sync-status

# Response: 200 OK
{
  "last_successful_sync": "2025-02-23T08:15:32Z",
  "sync_status": "success",
  "cverf_profiles_synced": 247,
  "cverf_cves_extracted": 3421,
  ...
}
```

### Debug Cyperf Connection

```bash
# Check if Cyperf controller is reachable
ping 52.32.20.150

# Test API connectivity (example with curl)
curl -k -u admin:CyPerf&Keysight#1 https://52.32.20.150/api/v2/profiles

# Check Docker container logs
docker logs <container_id> | grep -i cyperf
```

### Check Database State

```bash
# View recent syncs
sqlite3 cyperf_cve.db << 'EOF'
SELECT job_name, status, last_run_at, error_message, profiles_synced
FROM sync_metadata
ORDER BY last_run_at DESC
LIMIT 5;
EOF

# Count CVEs in database
sqlite3 cyperf_cve.db "SELECT COUNT(*) FROM cyperf_supported_cves;"

# List profiles synced
sqlite3 cyperf_cve.db << 'EOF'
SELECT DISTINCT attack_profile_name, COUNT(*) as cve_count
FROM cyperf_supported_cves
GROUP BY attack_profile_name
ORDER BY cve_count DESC
LIMIT 20;
EOF
```

### Common Errors & Solutions

**Error:** `CyperfConnectionError: Unable to connect to Cyperf Controller 52.32.20.150`

→ **Solution:** Check network connectivity, verify IP, check firewall rules

**Error:** `CyperfAPIError: Authentication failed`

→ **Solution:** Verify credentials in .env; test manually with curl

**Error:** `cyperf-api-wrapper not installed`

→ **Solution:** `pip install cyperf-api-wrapper`

**Error:** `Database error: FOREIGN KEY constraint failed`

→ **Solution:** CVE must exist in `cves` table before mapping can be created. Ensure NVD sync runs before Cyperf sync.

---

## Integration with NVD Sync

### Dependency Order

1. **NVD Sync** (fetch all CVE metadata from NVD API)
2. **Cyperf Sync** (map CVEs to attack profiles)

### Why?

The `cyperf_supported_cves` table has a foreign key constraint:
```sql
cve_id REFERENCES cves(id) ON DELETE CASCADE
```

If a CVE is not in the `cves` table, the upsert will fail with:
```
FOREIGN KEY constraint failed
```

### Handling

The `perform_sync()` function in `sync_service.py` doesn't explicitly require NVD data, but the database will reject inserts for CVEs not in the `cves` table.

**Solutions:**
1. **Preferred:** Run NVD sync first, then Cyperf sync
2. **Alternative:** Remove foreign key constraint (not recommended; loses data integrity)
3. **Safe Mode:** Catch FK errors and log warnings (retains stale data)

---

## Performance Considerations

### Expected Metrics

- **Profiles fetched:** 200-500 (typical Cyperf deployment)
- **CVEs extracted:** 2000-5000
- **Sync duration:** 2-5 seconds (network + parsing)
- **Database upsert:** 5-10 seconds (bulk transaction)
- **Total sync time:** 7-15 seconds

### Scaling Implications

**For 10,000+ CVEs:**
- Consider batching upserts (commit every 100 records)
- Profile extraction may require optimized parsing
- Database index performance critical

**For 100+ profiles:**
- API response may be paginated
- Adjust timeout settings if needed

---

## Next Steps (Phase 4+)

### Authentication & Authorization
- Add JWT middleware to admin endpoints
- Restrict sync trigger to admin users

### Monitoring & Alerts
- Prometheus metrics export (sync duration, success rate)
- Email alerts on 3+ consecutive failures
- Grafana dashboard for CVE coverage

### Advanced Features
- Incremental sync (fetch only changed profiles)
- Profile versioning (track profile changes over time)
- CVE deprecation tracking (mark profiles as deprecated)
- Webhook integration (notify external systems of sync completion)

### Testing
- Mock Cyperf API for unit tests
- Integration tests with real Cyperf Controller
- Chaos tests (network failures, timeouts)

---

## References

- **Cyperf Documentation:** [Keysight IxNetwork Cyperf](https://www.keysight.com/us/en/solutions/test-measurement/ixnetwork/cyperf.html)
- **NVD CVE Data:** [nvd.nist.gov](https://nvd.nist.gov)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **APScheduler:** [apscheduler.readthedocs.io](https://apscheduler.readthedocs.io)
- **SQLAlchemy:** [sqlalchemy.org](https://sqlalchemy.org)
