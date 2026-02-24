# Browse Tab Completion Plan

**Status**: Frontend redesigned ✓, API hooks corrected ✓, Backend infrastructure ready ✓
**Remaining**: Database population with CVE strike data

---

## Current State

### What's Done ✓
1. **Frontend UI**: Refined luxury design applied to Browse page
2. **API Integration**: Corrected `/cve/latest` endpoint parameters
   - Backend returns `results` (array of CVEDetail objects)
   - Each CVEDetail includes:
     - `id`, `description`, `published_date`
     - `cvss_v3_score`, `cvss_v4_score`
     - `cna` (CVE Numbering Authority)
     - **`testable`** (boolean - from cverf_cve_strike_mappings)
     - **`attack_profiles`** (array of strike names - from cverf_cve_strike_mappings)
3. **Backend**: Ready to serve data
   - `/cve/latest?page=1&limit=500` endpoint working
   - Joins with `cverf_cve_strike_mappings` table
   - NVD caching in Redis operational

### What's Missing ✗
1. **NVD CVE Data** - Need to fetch CVEs from NVD into `cves` table
2. **Cyperf Strike Mappings** - Need to sync strike profiles into `cverf_cve_strike_mappings` table

---

## How to Populate the Database

### Option A: Automatic Sync (Recommended)

**Trigger Manual Cyperf Sync:**

```bash
curl -X POST http://localhost:8000/api/admin/sync-cyperf
```

This will:
1. Fetch all CVE→Strike mappings from your Cyperf instance
2. Query NVD for recent CVEs (last 30 days)
3. Populate both `cves` and `cverf_cve_strike_mappings` tables
4. Write `/backend/data/cve_strikes.json` artifact

**Check Sync Status:**

```bash
curl http://localhost:8000/api/admin/sync-status
```

Response shows:
```json
{
  "last_successful_sync": "2026-02-23T20:15:30Z",
  "last_attempted_sync": "2026-02-23T20:15:25Z",
  "sync_status": "success",
  "cverf_profiles_synced": 1250,
  "cverf_cves_extracted": 4837,
  "error_message": null,
  "next_scheduled_sync": "2026-02-24T02:00:00Z"
}
```

### Option B: Test with Sample Data (If Cyperf Unavailable)

Create `backend/seed_sample_data.py`:

```python
import asyncio
from database import get_db_session
from db.cve import CVE
from db.cverf_cve_strike_mappings import CvrfCveStrikeMappings
from sqlalchemy import select

async def seed_data():
    session = await get_db_session()

    # Sample CVEs
    sample_cves = [
        CVE(
            id="CVE-2023-26360",
            description="Adobe ColdFusion Remote Code Execution",
            published_date="2023-02-14",
            cvss_v3_score=9.8,
            cvss_v3_severity="CRITICAL",
            cvss_v3_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            cna="Adobe"
        ),
        CVE(
            id="CVE-2023-38204",
            description="Adobe ColdFusion Insecure Deserialization",
            published_date="2023-08-09",
            cvss_v3_score=8.8,
            cvss_v3_severity="HIGH",
            cvss_v3_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
            cna="Adobe"
        ),
    ]

    session.add_all(sample_cves)
    await session.flush()

    # Sample Strike Mappings
    sample_mappings = [
        CvrfCveStrikeMappings(
            cve_id="CVE-2023-26360",
            strike_name="Adobe ColdFusion convertToTemplateProxy RCE"
        ),
        CvrfCveStrikeMappings(
            cve_id="CVE-2023-38204",
            strike_name="Adobe ColdFusion Deserialization"
        ),
    ]

    session.add_all(sample_mappings)
    await session.commit()
    await session.close()
    print("✓ Sample data seeded")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

Run: `cd backend && python seed_sample_data.py`

---

## Verification Workflow

### 1. Verify NVD Data Loaded

```bash
curl "http://localhost:8000/api/cve/search?id=CVE-2023-26360"
```

Should return:
```json
{
  "results": [{
    "id": "CVE-2023-26360",
    "description": "...",
    "cvss_v3_score": 9.8,
    "testable": false,
    "attack_profiles": []
  }],
  "total": 1,
  "query": "CVE-2023-26360",
  "search_type": "exact"
}
```

### 2. Verify Strike Mappings Loaded

```bash
curl "http://localhost:8000/api/cve/latest?page=1&limit=10"
```

Should include CVEs with:
- `testable: true` (if strike mappings exist)
- `attack_profiles: ["Strike Name 1", "Strike Name 2"]`

### 3. Test Browse Page in Browser

1. Start frontend dev server: `npm run dev` in `/frontend`
2. Open http://localhost:5173
3. Navigate to **Browse** tab
4. Verify:
   - ✓ CVE list loads without errors
   - ✓ Each row shows testability badge
   - ✓ Strike profiles visible if testable
   - ✓ Console has no errors

---

## Environment Requirements

For Cyperf sync to work, ensure these env vars are set in `/backend/.env`:

```bash
CYPERF_URL=https://your-cyperf-controller.com
CYPERF_API_KEY=your_api_key
CYPERF_API_SECRET=your_api_secret
```

Without these, sync will fail gracefully but retain previous data.

---

## Database Schema Reference

### cves table
```sql
id                  TEXT PRIMARY KEY
description         TEXT
published_date      DATE
cvss_v3_score       FLOAT
cvss_v3_severity    VARCHAR(10)
cvss_v3_vector      TEXT
cvss_v4_score       FLOAT (optional)
cvss_v4_severity    VARCHAR(10) (optional)
reference_urls      JSONB
cna                 VARCHAR(100)
```

### cverf_cve_strike_mappings table
```sql
cve_id              TEXT (FK → cves.id)
strike_name         TEXT
```

A CVE can have multiple strikes (one row per strike).

---

## Next Steps

**Immediate** (to get Browse working today):
1. Run `POST /admin/sync-cyperf` OR seed sample data
2. Test with `GET /api/cve/latest?page=1&limit=10`
3. Verify Browse page in browser

**Long-term**:
- Sync runs automatically at 02:00 UTC daily
- Admin can trigger manual sync anytime
- Data persists across app restarts

---

## Success Metrics

When complete, Browse page will:
- ✓ Load and display 10-500 CVEs per page
- ✓ Show testability badge (Testable / Not Testable)
- ✓ Display strike profiles for testable CVEs
- ✓ Support sorting by CVE ID, CVSS, published date
- ✓ Handle pagination (next, prev)
- ✓ Load in <1s from browser

**Phase 4 Success Criteria (from ROADMAP):**
- ✓ Dark theme with WCAG AA contrast
- ✓ Navigation bar with active page indicator
- ✓ Data table with column sorting
- ✓ "Can Cyperf Test?" badge visibility
- ✓ Status bar showing "Data last updated: X hours ago"
- ✓ Filter control for testable-only (if needed)

---

**Plan Created**: 2026-02-23
**Status**: Ready for execution
