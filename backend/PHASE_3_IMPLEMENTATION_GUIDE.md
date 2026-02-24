# Phase 3 Implementation Guide: Cyperf Integration + Sync Engine

## Overview

This guide walks through the complete Phase 3 implementation for Cyperf integration, including architecture decisions, code organization, and deployment considerations.

---

## Implementation Status

### Complete Components

✅ **Admin Endpoints**
- `POST /admin/sync-cyperf` — Manual sync trigger
- `GET /admin/sync-status` — Status monitoring

✅ **Database Models**
- `CyperfSupportedCVE` — CVE-to-profile mappings
- `SyncMetadata` — Sync job history and metadata

✅ **Service Layer**
- `CyperfService` — API client for Cyperf Controller
- `perform_sync()` — Main orchestration with retry logic

✅ **Scheduler**
- APScheduler configured for daily syncs at 02:00 UTC
- Support for manual trigger via endpoint

✅ **Error Handling**
- Graceful degradation (retains stale data on failure)
- Retry logic with exponential backoff (0s, 0s, 5s)
- Circuit breaker detection (3+ consecutive failures)

✅ **Logging & Monitoring**
- Structured logging at INFO/WARNING/ERROR levels
- Sync duration tracking
- Profile/CVE counts in logs

---

## Architecture Decision Records

### ADR-1: Graceful Degradation Over Hard Failures

**Decision:** On Cyperf connection errors, log the failure but retain all previous CVE mappings in the database.

**Rationale:**
- Users have access to last-known-good data
- Service remains partially functional even when Cyperf is unreachable
- Automatic retries ensure recovery without manual intervention
- No data corruption (transaction rollback on DB errors)

**Implementation:**
- `perform_sync()` catches all Cyperf errors
- `SyncMetadata` tracks status separately from CVE data
- GET `/admin/sync-status` returns status="failed" but keeps old CVE count

### ADR-2: Idempotent Upsert Pattern

**Decision:** Use SQLAlchemy's `session.merge()` for CVE-to-profile mappings.

**Rationale:**
- Prevents duplicate CVEs (unique constraint on cve_id)
- Safe to re-run sync multiple times (idempotent)
- Preserves creation timestamp (first_synced) on updates
- Updates sync timestamp (last_synced) on each run

**Implementation:**
```python
record = CyperfSupportedCVE(
    cve_id="CVE-2021-44228",
    attack_profile_name="Apache-Log4j-RCE",
    last_synced=datetime.utcnow(),
    is_deprecated=False,
)
merged = session.merge(record)
```

### ADR-3: Foreign Key Constraint for Data Integrity

**Decision:** `CyperfSupportedCVE.cve_id` references `CVEs.id` with ON DELETE CASCADE.

**Rationale:**
- Prevents orphaned CVE mappings
- Ensures NVD data and Cyperf mappings stay in sync
- Forces NVD sync before Cyperf sync

**Implementation:**
```sql
cve_id VARCHAR(20) UNIQUE NOT NULL
  REFERENCES cves(id) ON DELETE CASCADE
```

**Implication:** NVD sync must run before Cyperf sync (or CVE must exist in database)

### ADR-4: Async/Background Sync with APScheduler

**Decision:** Use APScheduler for scheduled syncs and allow manual trigger via endpoint.

**Rationale:**
- Non-blocking: sync runs in background, doesn't delay API responses
- Scheduled: automatic daily sync without human intervention
- Manual override: admins can force immediate sync for testing
- Resilient: retries on failure without user interaction

**Implementation:**
- `setup_scheduler()` initializes APScheduler with UTC timezone
- `sync_cyperf_job()` is the background task called by scheduler
- `trigger_cyperf_sync_now()` queues immediate one-time job
- Fallback to direct `perform_sync()` if scheduler not running

### ADR-5: Circuit Breaker for Alert Conditions

**Decision:** Log alert after 3+ consecutive sync failures.

**Rationale:**
- Prevents silent failures
- Alerts operators to systematic issues (e.g., Cyperf down)
- Allows monitoring systems to trigger escalations

**Implementation:**
```python
consecutive_failures = await SyncMetadata.get_consecutive_failures(session)
if consecutive_failures >= 3:
    logger.error(
        "Circuit breaker: 3 consecutive sync failures. "
        "Check Cyperf controller availability."
    )
```

---

## Code Organization

### Directory Structure

```
backend/
├── routes/
│   └── admin.py              (endpoints for sync trigger & status)
│
├── services/
│   ├── cyperf_service.py     (Cyperf API client)
│   └── sync_service.py       (orchestration with retry logic)
│
├── db/
│   ├── cyperf_mapping.py     (CyperfSupportedCVE ORM model)
│   └── sync_metadata.py      (SyncMetadata ORM model)
│
├── scheduler.py              (APScheduler setup & job functions)
├── config.py                 (Settings with validation)
├── database.py               (SQLAlchemy setup)
│
├── CYPERF_INTEGRATION.md         (Architecture & API reference)
├── CYPERF_API_EXAMPLES.md        (Mock data & examples)
└── PHASE_3_IMPLEMENTATION_GUIDE.md  (this file)
```

---

## Integration Points

### 1. Cyperf Controller (External)

**Endpoint:** `https://52.32.20.150/api/v2/attack-profiles`

**Credentials:**
- Username: `admin`
- Password: `CyPerf&Keysight#1`

**Response Schema:**
```json
{
  "attack_profiles": [
    {
      "id": "uuid",
      "name": "profile-name",
      "cves": ["CVE-2021-44228", ...]
    }
  ]
}
```

**Integration Path:**
```
CyperfService.__init__()
  ↓ (imports cyperf-api-wrapper)
CyperfApiClient(controller_address, username, password)
  ↓ (HTTPS connection)
52.32.20.150:443/api/v2/attack-profiles
```

### 2. NVD Database (Prerequisite)

**Requirement:** CVEs must exist in `cves` table before Cyperf mapping.

**Workflow:**
1. NVD Sync runs (fetches from NVD API, populates `cves` table)
2. Cyperf Sync runs (maps CVEs to profiles, populates `cyperf_supported_cves`)

**Error if out of order:**
```
FOREIGN KEY constraint failed
```

### 3. Redis (Optional Cache)

**Used for:** CVE query caching (not Cyperf sync)

**If unavailable:** Cache bypassed; API continues normally

---

## Deployment Checklist

### Pre-Deployment

- [ ] Cyperf credentials configured in `.env`
- [ ] Cyperf Controller reachable from deployment environment
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] NVD sync completed (populates `cves` table)
- [ ] Redis available (or plan for cache bypass)

### Deployment

- [ ] Deploy backend service
- [ ] Verify scheduler starts in logs
- [ ] Trigger manual sync: `POST /admin/sync-cyperf`
- [ ] Check status: `GET /admin/sync-status`
- [ ] Verify CVE counts are > 0

### Post-Deployment

- [ ] Monitor logs for sync errors
- [ ] Set up alerts for "Circuit breaker" messages
- [ ] Verify next scheduled sync time in status response
- [ ] Test manual trigger periodically

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_cyperf_service.py`

```python
import pytest
from services.cyperf_service import CyperfService

# Mock cyperf-api-wrapper
@pytest.fixture
def mock_cyperf_client(monkeypatch):
    def mock_get_all_profiles():
        return [
            {
                "id": "profile-1",
                "name": "Apache-Log4j-RCE",
                "cves": ["CVE-2021-44228"]
            }
        ]
    monkeypatch.setattr("cyperf_api_wrapper.CyperfApiClient.get_all_attack_profiles", mock_get_all_profiles)

# Test CVE extraction
def test_extract_cves_from_profiles():
    profiles = [
        {
            "name": "Apache-Log4j-RCE",
            "cves": ["CVE-2021-44228", "CVE-2021-44229"]
        }
    ]
    service = CyperfService("52.32.20.150", "admin", "pass")
    mappings = service.extract_cves_from_profiles(profiles)

    assert mappings == {
        "CVE-2021-44228": "Apache-Log4j-RCE",
        "CVE-2021-44229": "Apache-Log4j-RCE"
    }

# Test graceful error handling
@pytest.mark.asyncio
async def test_sync_handles_connection_error():
    # Mock Cyperf unreachable
    service = CyperfService("unreachable-ip", "admin", "pass")
    result = await service.sync_cyperf_cves()

    assert result.error is not None
    assert result.profiles_fetched == 0
    assert result.cves_extracted == 0
```

### Integration Tests

**File:** `tests/test_sync_service.py`

```python
import pytest
from services.sync_service import perform_sync
from database import SessionLocal
from config import Settings

@pytest.mark.asyncio
async def test_perform_sync_success(session, mock_cyperf):
    """Test full sync cycle with mock Cyperf."""
    settings = Settings(
        cyperf_controller_ip="mock.local",
        cyperf_username="admin",
        cyperf_password="test"
    )

    await perform_sync(session, settings)

    # Verify database state
    result = await session.execute(
        select(func.count(CyperfSupportedCVE.id))
    )
    count = result.scalar()
    assert count > 0

@pytest.mark.asyncio
async def test_manual_sync_endpoint(client):
    """Test POST /admin/sync-cyperf endpoint."""
    response = client.post("/admin/sync-cyperf")

    # Returns immediately (202 or 200)
    assert response.status_code in [200, 202]
    assert response.json()["status"] in ["sync_triggered", "sync_completed"]
```

### Manual Testing

**Trigger sync manually:**
```bash
curl -X POST http://localhost:8000/admin/sync-cyperf

# Response: 202 Accepted
{
  "status": "sync_triggered",
  "message": "Cyperf sync queued for immediate execution"
}
```

**Check status:**
```bash
curl http://localhost:8000/admin/sync-status | jq .

# Response: 200 OK
{
  "last_successful_sync": "2025-02-23T08:15:32Z",
  "sync_status": "success",
  "cverf_profiles_synced": 247,
  "cverf_cves_extracted": 3421,
  ...
}
```

**Check logs:**
```bash
docker logs <container_id> | grep -i cyperf | tail -20
```

---

## Troubleshooting Guide

### Issue: "cyperf-api-wrapper not installed"

**Error Message:**
```
CyperfConnectionError: cyperf-api-wrapper import failed: No module named 'cyperf_api_wrapper'
```

**Solution:**
```bash
pip install cyperf-api-wrapper
# OR
pip install -r requirements.txt
```

### Issue: "Unable to connect to Cyperf Controller"

**Error Message:**
```
CyperfConnectionError: Unable to connect to Cyperf Controller 52.32.20.150: [Errno 111] Connection refused
```

**Solutions:**
1. Verify IP address is correct: `ping 52.32.20.150`
2. Check firewall allows HTTPS (port 443)
3. Verify Cyperf service is running
4. Check credentials in `.env`

### Issue: "Authentication failed"

**Error Message:**
```
CyperfAPIError: Authentication failed: 401 Unauthorized
```

**Solutions:**
1. Verify username/password in `.env`
2. Check credentials haven't changed in Cyperf UI
3. Test manually with curl:
   ```bash
   curl -k -u admin:CyPerf&Keysight#1 https://52.32.20.150/api/v2/profiles
   ```

### Issue: "FOREIGN KEY constraint failed"

**Error Message:**
```
Database error: FOREIGN KEY constraint failed
```

**Solutions:**
1. Ensure NVD sync completed: Check `cves` table has data
   ```bash
   sqlite3 cyperf_cve.db "SELECT COUNT(*) FROM cves;"
   ```
2. Run NVD sync manually before Cyperf sync
3. Verify CVE IDs from Cyperf match NVD format (CVE-YYYY-XXXXX)

### Issue: Sync running but status shows "never"

**Cause:** Database query fails; sync metadata not recorded

**Solutions:**
1. Check database permissions
2. Verify database file location
3. Run migrations: `alembic upgrade head`
4. Check logs for database errors

---

## Performance Optimization

### For Large CVE Sets (10,000+)

**Current implementation:** Upserts all CVEs in single transaction

**Optimization:** Batch commits every N records
```python
BATCH_SIZE = 100
for i, (cve_id, profile_name) in enumerate(cve_mappings.items()):
    CyperfSupportedCVE.upsert_from_cyperf_data(session, cve_id, profile_name)

    if (i + 1) % BATCH_SIZE == 0:
        await session.commit()

await session.commit()  # Final commit
```

### For Large Profile Sets (500+)

**Current implementation:** Fetches all profiles at once

**Optimization:** Implement pagination in cyperf-api-wrapper
```python
profiles = []
page = 1
while True:
    page_data = client.get_all_attack_profiles(page=page, per_page=100)
    if not page_data:
        break
    profiles.extend(page_data)
    page += 1
```

### Index Performance

**Current:** Indexes on `cve_id` and `attack_profile_name`

**Monitor:** Query performance on large datasets
```sql
EXPLAIN QUERY PLAN
SELECT * FROM cyperf_supported_cves
WHERE attack_profile_name = 'Apache-Log4j-RCE';
```

---

## Monitoring & Observability

### Metrics to Track

1. **Sync Success Rate:** % of successful syncs
2. **Sync Duration:** Time from start to finish
3. **CVE Growth:** # of CVEs in database over time
4. **Profile Coverage:** # of unique profiles

### Log Analysis

**Successful sync indicators:**
```
INFO     ✓ Fetched 247 attack profiles from Cyperf in 2.34s
INFO     ✓ Extracted 3421 CVE-to-profile mappings
INFO     ✓ Cyperf sync SUCCEEDED: 247 profiles, 3421 CVEs
```

**Error indicators:**
```
ERROR    Cyperf sync FAILED after 3 attempts: Connection error
ERROR    Circuit breaker: 3 consecutive sync failures
```

### Grafana Dashboard Queries

**Sync success rate:**
```
count(sync_status="success") / count(sync_status in ["success", "failed"])
```

**CVE count over time:**
```
SELECT last_sync_time, COUNT(*) FROM cyperf_supported_cves GROUP BY last_sync_time
```

---

## Future Enhancements (Phase 4+)

### Authentication & Authorization
- JWT token validation for admin endpoints
- Role-based access control (admin-only)

### Incremental Sync
- Track profile versions
- Only update changed profiles
- Reduce network bandwidth

### Webhooks
- Notify external systems on sync completion
- Integration with SOAR/ticketing systems

### Advanced Monitoring
- Prometheus metrics export
- Email/Slack alerts on failures
- Dashboard for CVE coverage

### Profile Deprecation
- Track when profiles are removed
- Mark CVEs as deprecated
- Archive historical mappings

---

## References

- **Cyperf Documentation:** [Keysight IxNetwork Cyperf](https://www.keysight.com/us/en/solutions/test-measurement/ixnetwork/cyperf.html)
- **APScheduler:** [apscheduler.readthedocs.io](https://apscheduler.readthedocs.io)
- **SQLAlchemy Async:** [sqlalchemy.org/async](https://sqlalchemy.org/async)
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)

---

## Glossary

- **Attack Profile:** Cyperf's term for a security test/attack scenario (e.g., Apache-Log4j-RCE)
- **CVE:** Common Vulnerabilities and Exposures (e.g., CVE-2021-44228)
- **Idempotent:** Operation that produces same result if run once or multiple times
- **Graceful Degradation:** System remains partially functional even when components fail
- **Circuit Breaker:** Pattern to prevent cascading failures by detecting repeated errors
- **Foreign Key:** Database constraint ensuring referential integrity

---

## Questions & Support

For implementation questions, refer to:
1. `CYPERF_INTEGRATION.md` — Architecture & concepts
2. `CYPERF_API_EXAMPLES.md` — API responses & examples
3. Code comments in `services/cyperf_service.py` and `routes/admin.py`
4. Git history for design rationale

