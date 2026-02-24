# Cyperf Integration - Quick Start Guide

For rapid deployment and testing of Phase 3 Cyperf sync integration.

---

## 1. Environment Setup (5 minutes)

### Configure .env

```bash
# Create .env in backend/ directory
cat > backend/.env << 'EOF'
# Cyperf Controller
CYPERF_CONTROLLER_IP=52.32.20.150
CYPERF_USERNAME=admin
CYPERF_PASSWORD=CyPerf&Keysight#1

# Sync Configuration
CYPERF_SYNC_INTERVAL_HOURS=24

# Database
DATABASE_URL=sqlite+aiosqlite:///./cyperf_cve.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF
```

### Install Dependencies

```bash
cd backend/
pip install -r requirements.txt
```

---

## 2. Database Initialization (2 minutes)

### Run Migrations

```bash
# Apply all migrations to create tables
alembic upgrade head

# Verify tables created
sqlite3 cyperf_cve.db ".tables"
```

### Seed Test CVEs (if needed)

```python
# Optional: Add test CVEs to database
python << 'EOF'
import asyncio
from sqlalchemy import insert
from database import async_engine
from db.cve import CVE
from datetime import datetime

async def seed_cves():
    async with async_engine.begin() as conn:
        cves = [
            {"id": "CVE-2021-44228", "description": "Log4j RCE"},
            {"id": "CVE-2021-44229", "description": "Log4j RCE variant"},
            {"id": "CVE-2021-26855", "description": "Exchange ProxyLogon"},
        ]
        stmt = insert(CVE).values(cves)
        await conn.execute(stmt)
        await conn.commit()

asyncio.run(seed_cves())
EOF
```

---

## 3. Start the Application (2 minutes)

### Development Mode

```bash
cd backend/
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image
docker build -t cyperf-api:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  -e CYPERF_CONTROLLER_IP=52.32.20.150 \
  -e CYPERF_USERNAME=admin \
  -e CYPERF_PASSWORD='CyPerf&Keysight#1' \
  --name cyperf-api \
  cyperf-api:latest

# View logs
docker logs -f cyperf-api
```

---

## 4. Verify Installation (3 minutes)

### Check Health Endpoint

```bash
curl http://localhost:8000/health
# Response: 200 OK
{
  "status": "ok",
  "service": "Cyperf CVE Tracker"
}
```

### Check Sync Status

```bash
curl http://localhost:8000/admin/sync-status | jq .
# Response: 200 OK
{
  "last_successful_sync": null,
  "sync_status": "never",
  "cverf_profiles_synced": 0,
  "cverf_cves_extracted": 0,
  "error_message": null,
  "next_scheduled_sync": null
}
```

---

## 5. Trigger First Sync (5 minutes)

### Manual Sync Trigger

```bash
# Queue immediate sync
curl -X POST http://localhost:8000/admin/sync-cyperf

# Response: 202 Accepted
{
  "status": "sync_triggered",
  "message": "Cyperf sync queued for immediate execution"
}
```

### Monitor Sync Progress

```bash
# Watch logs in real-time
docker logs -f cyperf-api | grep -i cyperf

# Expected output:
# INFO     Starting Cyperf sync operation...
# INFO     Cyperf sync attempt 1/3...
# INFO     ✓ Fetched 247 attack profiles from Cyperf in 2.34s
# INFO     ✓ Extracted 3421 CVE-to-profile mappings
# INFO     ✓ Cyperf sync SUCCEEDED: 247 profiles, 3421 CVEs
```

### Check Results

```bash
# Wait 5 seconds for sync to complete, then check status
sleep 5
curl http://localhost:8000/admin/sync-status | jq .

# Response: 200 OK
{
  "last_successful_sync": "2025-02-23T08:15:32Z",
  "sync_status": "success",
  "cverf_profiles_synced": 247,
  "cverf_cves_extracted": 3421,
  "error_message": null,
  "next_scheduled_sync": "2025-02-24T02:00:00Z"
}
```

---

## 6. Verify Database

### Count CVEs

```bash
sqlite3 cyperf_cve.db << 'EOF'
SELECT COUNT(*) as total_cves FROM cyperf_supported_cves;
SELECT COUNT(DISTINCT attack_profile_name) as total_profiles FROM cyperf_supported_cves;
EOF

# Expected output:
# 3421
# 247
```

### View Sample Data

```bash
sqlite3 cyperf_cve.db << 'EOF'
SELECT cve_id, attack_profile_name, last_synced
FROM cyperf_supported_cves
LIMIT 10;
EOF
```

### Check Sync History

```bash
sqlite3 cyperf_cve.db << 'EOF'
SELECT job_name, status, last_run_at, profiles_synced, error_message
FROM sync_metadata;
EOF
```

---

## 7. Query CVEs

### Find Testable CVEs

```bash
# Get CVE that has Cyperf profile
curl 'http://localhost:8000/cves/CVE-2021-44228' | jq '.testable'
# Response: true

# Get CVE details with profile
curl 'http://localhost:8000/cves/CVE-2021-44228' | jq '.attack_profile'
# Response: "Apache-Log4j-RCE"
```

### List All Testable CVEs

```bash
# Filter for CVEs with testable=true
curl 'http://localhost:8000/cves?testable=true' | jq '.items | length'
# Response: 3421
```

---

## 8. Troubleshooting

### Sync Fails: Connection Refused

```bash
# Check if Cyperf is reachable
ping 52.32.20.150

# Check if port 443 is open
telnet 52.32.20.150 443

# Check credentials
curl -k -u admin:CyPerf&Keysight#1 \
  https://52.32.20.150/api/v2/attack-profiles
```

### Sync Fails: Authentication Error

```bash
# Verify credentials in .env
cat backend/.env | grep CYPERF

# Test credentials directly
curl -k -u admin:'CyPerf&Keysight#1' \
  https://52.32.20.150/api/v2/attack-profiles \
  -v
```

### Database Error: Foreign Key Constraint

```bash
# Ensure CVEs exist before Cyperf sync
sqlite3 cyperf_cve.db "SELECT COUNT(*) FROM cves;"

# If empty, run NVD sync first or seed CVEs
python << 'EOF'
import asyncio
from database import async_engine
from db.cve import CVE
from datetime import datetime
from sqlalchemy import insert

async def seed():
    async with async_engine.begin() as conn:
        cves = [
            {"id": "CVE-2021-44228", "description": "Log4j RCE"},
        ]
        stmt = insert(CVE).values(cves)
        await conn.execute(stmt)
        await conn.commit()

asyncio.run(seed())
EOF
```

### Scheduler Not Starting

```bash
# Check if APScheduler is available
python -c "from apscheduler.schedulers.asyncio import AsyncIOScheduler; print('OK')"

# If error, install
pip install apscheduler>=3.10

# Check logs for scheduler errors
docker logs cyperf-api | grep -i scheduler
```

---

## 9. Scheduled Sync (Automatic)

### Daily Sync Schedule

By default, sync runs automatically at **02:00 UTC** each day with **±5 minute jitter**.

**To change schedule**, edit `scheduler.py`:
```python
# Current: 02:00 UTC daily
scheduler.add_job(
    sync_cyperf_job,
    trigger=CronTrigger(hour=2, minute=0, timezone="UTC", jitter=300),
    ...
)

# Change to 23:00 UTC (11 PM) daily:
trigger=CronTrigger(hour=23, minute=0, timezone="UTC", jitter=300),

# Change to every 12 hours:
trigger=CronTrigger(hour="*/12", minute=0, timezone="UTC", jitter=300),
```

---

## 10. Production Deployment

### Pre-Flight Checklist

- [ ] `.env` configured with real Cyperf credentials
- [ ] Cyperf Controller reachable from deployment network
- [ ] Database migrations applied
- [ ] NVD sync completed (CVEs table has data)
- [ ] Redis available or cache bypass confirmed
- [ ] Logs configured and monitored
- [ ] Monitoring/alerts set up for "Circuit breaker" messages

### Deploy

```bash
# Build production image
docker build -t cyperf-api:v1.0.0 .

# Push to registry (adjust registry URL)
docker tag cyperf-api:v1.0.0 myregistry.azurecr.io/cyperf-api:v1.0.0
docker push myregistry.azurecr.io/cyperf-api:v1.0.0

# Deploy to Kubernetes/Docker Swarm
kubectl apply -f k8s/cyperf-api-deployment.yaml
```

### Monitor in Production

```bash
# View sync history (SQLite)
sqlite3 cyperf_cve.db "SELECT * FROM sync_metadata ORDER BY last_run_at DESC LIMIT 5;"

# Set up log aggregation
# Configure ELK Stack, Splunk, Datadog, etc. to ingest container logs

# Set up alerts
# Alert on: sync_status="failed" OR "Circuit breaker" in logs
```

---

## 11. API Reference

### Endpoints

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| `GET` | `/admin/sync-status` | Check last sync | `SyncStatusResponse` |
| `POST` | `/admin/sync-cyperf` | Trigger manual sync | `{"status": "sync_triggered"}` |
| `GET` | `/cves/{cve_id}` | Get CVE details | `CVEResponse` |
| `GET` | `/cves?testable=true` | List testable CVEs | `CVEListResponse` |
| `GET` | `/health` | Health check | `{"status": "ok"}` |

### Response Models

**SyncStatusResponse:**
```json
{
  "last_successful_sync": "2025-02-23T08:15:32Z",
  "last_attempted_sync": "2025-02-23T08:15:32Z",
  "sync_status": "success|failed|running|never",
  "cverf_profiles_synced": 247,
  "cverf_cves_extracted": 3421,
  "error_message": null,
  "next_scheduled_sync": "2025-02-24T02:00:00Z"
}
```

**CVEResponse:**
```json
{
  "id": "CVE-2021-44228",
  "description": "Remote code execution in Apache Log4j",
  "published_date": "2021-12-10T00:00:00Z",
  "cvss_v3_score": 10.0,
  "cvss_v3_severity": "CRITICAL",
  "testable": true,
  "attack_profile": "Apache-Log4j-RCE"
}
```

---

## 12. Key Files & Documentation

| File | Purpose |
|------|---------|
| `CYPERF_INTEGRATION.md` | Architecture & design |
| `CYPERF_API_EXAMPLES.md` | Mock data & examples |
| `CYPERF_API_CLIENT_SPEC.md` | Wrapper interface spec |
| `PHASE_3_IMPLEMENTATION_GUIDE.md` | Complete implementation guide |
| `routes/admin.py` | API endpoints |
| `services/cyperf_service.py` | Cyperf client |
| `services/sync_service.py` | Sync orchestration |
| `scheduler.py` | APScheduler setup |

---

## 13. Common Commands

```bash
# Start app
cd backend && uvicorn main:app --reload

# Run tests
pytest backend/tests/test_cyperf_integration.py -v

# Check database
sqlite3 cyperf_cve.db ".schema cyperf_supported_cves"

# View logs
docker logs -f cyperf-api | grep cyperf

# Trigger sync
curl -X POST http://localhost:8000/admin/sync-cyperf

# Check status
curl http://localhost:8000/admin/sync-status | jq .

# Query CVE
curl http://localhost:8000/cves/CVE-2021-44228 | jq .

# Count CVEs
sqlite3 cyperf_cve.db "SELECT COUNT(*) FROM cyperf_supported_cves;"
```

---

## Next Steps

1. Deploy to development environment
2. Verify sync completes successfully
3. Monitor logs for 24 hours
4. Adjust schedule if needed
5. Deploy to production
6. Set up monitoring and alerts
7. Document any custom configurations

---

## Support

For issues or questions, see:
- `CYPERF_INTEGRATION.md` — Architecture section
- `PHASE_3_IMPLEMENTATION_GUIDE.md` — Troubleshooting section
- Code comments in `services/cyperf_service.py`
- Git history for design rationale
