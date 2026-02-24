# Cyperf CVE Tracker - System Architecture

**Document Version:** 1.0
**Last Updated:** 2026-02-24
**Author:** Architecture Team
**Audience:** Engineering Team

---

## Executive Summary

The Cyperf CVE Tracker is a web application that bridges Keysight's Cyperf testing platform with CVE (Common Vulnerabilities and Exposures) data, enabling security teams to identify which vulnerabilities their Cyperf deployment can test. The system follows a three-tier architecture: React frontend, FastAPI backend, and PostgreSQL database, orchestrated via Docker containers with Redis caching for performance.

**Core Value Proposition:** Remove guesswork from vulnerability testing decisions by providing a unified interface showing CVE metadata alongside Cyperf testing capability.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Container Infrastructure](#container-infrastructure)
3. [API Layer](#api-layer)
4. [Backend Services](#backend-services)
5. [Frontend Application](#frontend-application)
6. [Database Schema](#database-schema)
7. [Data Synchronization Pipeline](#data-synchronization-pipeline)
8. [Caching Strategy](#caching-strategy)
9. [Deployment & Startup](#deployment--startup)
10. [Error Handling & Resilience](#error-handling--resilience)
11. [Performance & Scaling](#performance--scaling)
12. [Key Design Decisions](#key-design-decisions)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
│                  (Vite dev server on :3000)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Frontend Layer (React + Vite)                   │
│  - Search CVEs by ID                                        │
│  - Browse all synced CVEs (2195 from Cyperf)               │
│  - View CVE details + Cyperf strike profiles                │
│  - Manual sync trigger                                      │
└────────────────────────┬────────────────────────────────────┘
                         │ /api/* proxy
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Backend API Layer (FastAPI on :8000)             │
│  - /cve/search      - Search CVEs by ID                    │
│  - /cve/latest      - Paginated CVE browse (all 2195)      │
│  - /admin/sync-cyperf - Trigger manual sync                │
│  - /admin/sync-status - Get last sync timestamp            │
│  - /health          - Health check                         │
└────────────┬──────────────────────────┬────────────────────┘
             │                          │
        ┌────▼──────┐            ┌──────▼────┐
        │ PostgreSQL │            │   Redis    │
        │ Database   │            │   Cache    │
        │ (:5432)    │            │   (:6379)  │
        └───────────┘            └────────────┘
             │
        ┌────▼─────────────────────────────────────┐
        │  External Services                       │
        │  - NVD API (CVE metadata)                │
        │  - Cyperf API (strike profiles)          │
        └────────────────────────────────────────┘
```

---

## Container Infrastructure

### Docker Compose Setup

The application runs in 3 containerized services:

#### 1. **API Service** (`cyperf_api_dev`)
```yaml
Service: FastAPI application
Image: claudeexp-api (built from backend/Dockerfile)
Port: 8000
Environment:
  - DATABASE_URL=postgresql://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev
  - REDIS_URL=redis://redis:6379/0
  - CYPERF_CONTROLLER_IP=<credentials from environment>
  - NVD_API_KEY=<optional, increases rate limit>
Startup:
  - Migrates database via Alembic
  - Initializes Redis connection pool
  - Starts APScheduler for background Cyperf sync
  - Triggers immediate startup sync
Health Check: GET /health (returns 200 when ready)
```

#### 2. **Database Service** (`cyperf_db_dev`)
```yaml
Service: PostgreSQL 15
Image: postgres:15-alpine
Port: 5432
Database: cyperf_cve_dev
User: cyperf_dev
Password: cyperf_dev_password
Volumes: postgres_data (persistent)
Startup: Initializes empty database (migrations run in API container)
```

#### 3. **Cache Service** (`cyperf_cache_dev`)
```yaml
Service: Redis 7
Image: redis:7-alpine
Port: 6379
Volumes: redis_data (persistent)
Usage: CVE metadata cache, rate-limit tracking
TTL: 24 hours (1h ±5min jitter to prevent thundering herd)
```

### Startup Sequence

```
1. docker-compose up -d
   ├─ Start postgres container
   ├─ Start redis container
   ├─ Start api container
   │  ├─ Alembic migrates database schema
   │  ├─ Connect to PostgreSQL
   │  ├─ Connect to Redis
   │  ├─ Initialize APScheduler
   │  ├─ Queue immediate Cyperf sync job
   │  └─ Start FastAPI application
   └─ Services report healthy when /health returns 200

2. docker-compose restart api
   ├─ Gracefully shutdown existing container
   ├─ Restart fresh API container
   ├─ Triggers startup sync again (idempotent)
   └─ Full CVE database refresh on restart

Time to Ready: ~10-15 seconds after `docker-compose up`
```

---

## API Layer

### REST Endpoints

All API calls use JSON. Base URL: `http://localhost:8000` (or via `/api` proxy in frontend dev mode).

#### **GET /cve/search**
Search for CVEs by ID with optional severity filter.

```bash
# Exact match
GET /cve/search?id=CVE-2023-26360

# Prefix/wildcard
GET /cve/search?id=CVE-2023-*

# With severity filter
GET /cve/search?id=CVE-2023-*&severity=HIGH

# Response
{
  "results": [
    {
      "id": "CVE-2023-26360",
      "description": "Adobe ColdFusion RCE...",
      "published_date": "2023-03-23T20:15:15.263000+00:00",
      "cvss_v3_score": 8.6,
      "cvss_v3_severity": "HIGH",
      "cvss_v3_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N",
      "cvss_v4_score": null,
      "cvss_v4_severity": null,
      "cvss_v4_vector": null,
      "reference_urls": ["https://..."],
      "cna": null,
      "testable": true,
      "attack_profiles": [
        "Strike Adobe ColdFusion convertToTemplateProxy Insecure Deserialization"
      ]
    }
  ],
  "total": 1,
  "query": "CVE-2023-26360",
  "search_type": "exact"
}
```

**Search Dispatch Logic:**
1. **Exact Match (Tier 1):** CVE ID exactly matches pattern `CVE-YYYY-NNNNN`
   - Checks Redis cache first (24h TTL)
   - On cache miss: queries NVD API with retry logic
   - On NVD failure: falls back to PostgreSQL
2. **Prefix Match (Tier 2):** CVE ID contains wildcard `*` (e.g., `CVE-2023-*`)
   - Queries PostgreSQL with SQL LIKE pattern
   - No NVD query (avoids rate-limit exhaustion)
3. **Fuzzy Match (Tier 3):** Partial CVE ID (e.g., `2023-26360`)
   - Uses RapidFuzz token_sort_ratio scorer
   - Only searches local PostgreSQL (not NVD live)

**Rate Limiting:**
- NVD: 10 req/sec without API key, 100 req/sec with key
- On 429 (rate-limit): retries 3x with exponential backoff, serves stale cache or returns 503

#### **GET /cve/latest**
Paginated browse of all 2195 testable CVEs from Cyperf.

```bash
# Get all CVEs in one request
GET /cve/latest?page=1&limit=2500

# Paginated (500 per page)
GET /cve/latest?page=1&limit=500
GET /cve/latest?page=2&limit=500

# With severity filter
GET /cve/latest?severity=HIGH&limit=2500

# Response
{
  "results": [
    { /* CVEDetail object */ }
  ],
  "total": 500,           // Results on this page
  "page": 1,
  "page_size": 500,
  "severity_filter": null
}
```

**Implementation Notes:**
- Queries `cverf_cve_strike_mappings` table as source of truth
- LEFT JOINs with `cves` table to augment NVD metadata
- Returns synthetic CVE record for CVEs without NVD data:
  ```json
  {
    "id": "CVE-1999-0067",
    "description": "CVE from Cyperf; NVD metadata not available",
    "published_date": null,
    "cvss_v3_score": null,
    "testable": true,
    "attack_profiles": ["Strike PHF Qname Parameter Command Execution"]
  }
  ```
- Supports limit up to 2500 (covers all Cyperf CVEs)
- Sorting: by CVE ID (alphabetical)
- Severity filter: OR semantics (v3.1 OR v4.0 must match)

#### **POST /admin/sync-cyperf**
Manually trigger a Cyperf CVE sync outside the normal schedule.

```bash
POST /admin/sync-cyperf

# Response (202 Accepted)
{
  "message": "Cyperf sync queued",
  "job_id": "manual_sync_1708873400"
}
```

**Behavior:**
- Queues an immediate background job in APScheduler
- Returns 202 Accepted (async operation)
- Sync runs in background without blocking API response
- Idempotent: safe to call multiple times

#### **GET /admin/sync-status**
Get timestamp and status of last Cyperf sync.

```bash
GET /admin/sync-status

# Response
{
  "last_sync_timestamp": "2026-02-24T02:35:37Z",
  "last_sync_duration_seconds": 29.12,
  "cves_synced": 2195,
  "status": "success",
  "error_message": null
}
```

#### **GET /health**
Health check endpoint for container orchestration.

```bash
GET /health

# Response (200 OK when healthy, 503 when degraded)
{
  "status": "healthy",
  "dependencies": {
    "database": "ok",
    "redis": "ok",
    "scheduler": "ok"
  }
}
```

### Error Handling

All errors return structured JSON:

```json
{
  "error": "CVE_NOT_FOUND",
  "message": "CVE 'CVE-2024-99999' not found in NVD or local cache",
  "detail": null
}
```

**HTTP Status Codes:**
- `200 OK` - Successful response
- `202 Accepted` - Async operation queued (sync-cyperf)
- `404 Not Found` - CVE not found in exact search
- `422 Unprocessable Entity` - Invalid query parameters
- `503 Service Unavailable` - NVD exhausted, no cached data available

---

## Backend Services

### Service Layer Architecture

```
routes/
├── cve.py          # /cve/* endpoints
├── admin.py        # /admin/* endpoints
└── health.py       # /health endpoint
    │
    ▼ Depends on
services/
├── cve_service.py          # CVE search & browse orchestration
├── nvd_service.py          # NVD API client with retry logic
├── cyperf_service.py       # Cyperf API client
├── sync_service.py         # Cyperf sync orchestration
├── cache_service.py        # Redis cache abstraction
└── sync_metadata.py        # Sync history tracking
    │
    ▼ Depends on
database/
├── cve.py                  # ORM: CVEs table
├── cverf_cve_strike_mappings.py  # ORM: Cyperf mappings
└── sync_metadata.py        # ORM: Sync history
```

### Key Service Classes

#### **CveService.get_latest_cves()**
Fetches paginated CVEs for browse page.

```python
async def get_latest_cves(
    page: int,
    page_size: int,
    severity: str | None,
    nvd: NVDClient,
    db: AsyncSession,
    cache: CVECacheService,
) -> tuple[list[dict], int]:
    """
    1. Optional: refresh DB from NVD (non-blocking on failure)
    2. Query cverf_cve_strike_mappings for distinct CVE IDs (pagination)
    3. LEFT JOIN with cves table for NVD metadata
    4. Batch-load strike names for each CVE
    5. Apply severity filter (OR semantics)
    6. Return paginated results
    """
```

**Behavior:**
- Cyperf data is source of truth (returns ALL mappings)
- NVD data augments when available (CVE metadata)
- Non-blocking NVD failure (serves stale cache)
- Severity filter uses OR logic: `(cvss_v3_severity = 'HIGH') OR (cvss_v4_severity = 'HIGH')`

#### **CyperfService.fetch_cve_strike_mappings()**
Connects to Cyperf controller and extracts CVE→Strike pairs.

```python
async def fetch_cve_strike_mappings(self) -> dict[str, list[str]]:
    """
    1. Authenticate with Cyperf controller (SSH key-based)
    2. Call ApplicationResourcesApi.get_resources_strikes()
    3. Parse JSON response: { "CVE-YYYY-NNNNN": "Strike Name", ... }
    4. Aggregate multiple strikes per CVE
    5. Return dict: { "CVE-2023-26360": ["Strike1", "Strike2"], ... }
    """
```

**API Used:**
- Keysight's `cyperf-api-wrapper` library (v7.0.6)
- Endpoint: `ApplicationResourcesApi.get_resources_strikes()`
- Returns: JSON mapping of 2195 unique CVE IDs to strike names

#### **SyncService.perform_sync()**
Orchestrates full Cyperf sync with retry logic and graceful degradation.

```python
async def perform_sync(
    session: AsyncSession,
    settings: Settings
) -> None:
    """
    1. Record sync attempt start in sync_metadata
    2. Retry loop (3 attempts: immediate, immediate, +5s delay):
       a. Create CyperfService instance
       b. Call fetch_cve_strike_mappings()
       c. Atomic full-replace:
          - DELETE all rows from cverf_cve_strike_mappings
          - INSERT fresh mappings
       d. Write JSON artifact to ./data/cve_strikes.json
       e. Record sync completion (success/failure)
    3. Circuit breaker: stop retry after 3 consecutive failures
    """
```

**Guarantees:**
- **Atomicity:** All-or-nothing: either full new data or retain old (no partial)
- **Idempotency:** Safe to call multiple times (full replace, not delta)
- **Non-fatal failures:** Errors don't crash scheduler; recorded in metadata
- **Graceful degradation:** Cyperf downtime = stale data, not HTTP 500

---

## Frontend Application

### Technology Stack

- **Framework:** React 18 + Vite 5.4
- **Styling:** Tailwind CSS 3 + shadcn/ui components
- **HTTP Client:** Axios with React Query
- **Routing:** React Router v6
- **State Management:** React Query (via hooks)

### Page Structure

```
src/
├── pages/
│   ├── SearchPage.tsx       # /search - Exact CVE lookup
│   ├── BrowsePage.tsx       # /browse - All 2195 CVEs with search/sort
│   └── BatchPage.tsx        # /batch - Bulk operations (future)
│
├── components/
│   ├── layout/
│   │   ├── Navigation.tsx    # Header with sync button
│   │   └── StatusBar.tsx     # Footer with last sync timestamp
│   │
│   └── shared/
│       ├── DataTable.tsx     # CVE table with sorting
│       ├── Badge.tsx         # Testable/Not Testable indicator (GREEN)
│       └── StaleDataWarning.tsx  # Banner when sync is stale
│
├── hooks/
│   └── useAPI.ts            # Custom React Query hooks
│       ├── useSearchCVE(id)  # /cve/search
│       ├── useLatestCVEs(page, pageSize) # /cve/latest
│       └── useSyncStatus()   # /admin/sync-status
│
└── types/
    └── api.ts               # TypeScript interfaces for API responses
```

### Browse Page UX Flow

```
1. User opens /browse
2. Component mounts
3. Calls useLatestCVEs(1, 2500)
   ├─ React Query caches response
   ├─ Frontend makes HTTP GET /api/cve/latest?page=1&limit=2500
   └─ Backend returns 2195 CVEs
4. DataTable renders:
   ├─ Columns: CVE ID | CVSS Score | Published Date | Testable (GREEN) | Strike Profiles
   ├─ Client-side filtering: search by CVE ID or strike name
   ├─ Client-side sorting: click column header
   └─ No pagination (all 2195 loaded once)
5. Sync Status
   ├─ useSyncStatus() polls every 5 minutes
   └─ StatusBar shows "Last synced: 2026-02-24 02:35:37Z"
```

### Design System

**Color Palette (Refined Luxury Aesthetic):**
- Primary Accent: Gold (#d4af37) - used for highlights, buttons
- **Testable Badge: Bright Green (#22c55e)** - indicates CVE is testable by Cyperf
- Background: Deep Charcoal (#0A0E14)
- Text: Warm Cream (#f5f1e8)
- Borders: Subtle Gray (#3f4349)

**Typography:**
- Display Font: Playfair Display (serif, elegant)
- Body Font: System fonts (efficient)

---

## Database Schema

### PostgreSQL 15 Schema

#### **Table: `cves` (CVE metadata from NVD)**

```sql
CREATE TABLE cves (
    id VARCHAR(20) PRIMARY KEY,                 -- CVE-YYYY-NNNNN
    description TEXT,                           -- Full vulnerability description
    published_date TIMESTAMP WITH TIME ZONE,    -- When NVD published
    cvss_v3_score DECIMAL(3,1),                 -- CVSS 3.1 base score (0.0-10.0)
    cvss_v3_severity VARCHAR(20),               -- LOW | MEDIUM | HIGH | CRITICAL
    cvss_v3_vector VARCHAR(255),                -- CVSS 3.1 vector string
    cvss_v4_score DECIMAL(3,1),                 -- CVSS 4.0 base score (0.0-10.0)
    cvss_v4_severity VARCHAR(20),               -- LOW | MEDIUM | HIGH | CRITICAL
    cvss_v4_vector VARCHAR(255),                -- CVSS 4.0 vector string
    references TEXT,                            -- JSON array of URLs
    first_seen TIMESTAMP DEFAULT now(),         -- When first loaded into DB
    INDEX idx_published_date (published_date DESC),
    INDEX idx_cvss_v3_severity (cvss_v3_severity)
);

-- Current size: ~512 records (only CVEs that exist in NVD or Redis cache)
-- Note: Most Cyperf CVEs don't have NVD data (they're from 1999-2005)
```

#### **Table: `cverf_cve_strike_mappings` (Cyperf test capability)**

```sql
CREATE TABLE cverf_cve_strike_mappings (
    cve_id VARCHAR(20),                         -- FK to Cyperf (no constraint)
    strike_name VARCHAR(500),                   -- Cyperf Strike profile name
    PRIMARY KEY (cve_id, strike_name),          -- Composite key
    INDEX idx_cve_id (cve_id),
    INDEX idx_strike_name (strike_name)
);

-- Current size: 2195 records (one row per CVE-Strike pair)
-- Example:
-- CVE-2023-26360 | Strike Adobe ColdFusion convertToTemplateProxy Insecure Deserialization
-- CVE-1999-0067  | Strike PHF Qname Parameter Command Execution
-- CVE-2021-27275 | Strike Netgear ProSAFE NMS300 ConfigFileController Directory Traversal Arbitrary File Read Vulnerability

-- All CVEs shown in Browse tab come from this table
-- This is the source of truth for "testable" designation
```

#### **Table: `sync_metadata` (Cyperf sync history)**

```sql
CREATE TABLE sync_metadata (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255),                      -- "cyperf_profiles"
    status VARCHAR(20),                         -- "started" | "success" | "failed"
    started_at TIMESTAMP WITH TIME ZONE,        -- When sync began
    completed_at TIMESTAMP WITH TIME ZONE,      -- When sync finished
    duration_seconds FLOAT,                     -- Total execution time
    cves_count INT,                             -- Number of CVEs synced (2195)
    profiles_count INT,                         -- Alias for cves_count
    error_message TEXT,                         -- If status=failed
    next_sync_scheduled TIMESTAMP WITH TIME ZONE, -- When next sync is scheduled
    INDEX idx_job_name (job_name),
    INDEX idx_completed_at (completed_at DESC)
);

-- Current size: 1 record (most recent sync)
-- Used by /admin/sync-status endpoint to show UI status banner
```

#### **Table: `alembic_version` (Migration tracking)**

```sql
-- Managed by Alembic ORM
-- Tracks which database migrations have been applied
-- Auto-created, no manual intervention needed
```

### Query Patterns

**Get all testable CVEs with metadata:**
```sql
SELECT DISTINCT
  m.cve_id,
  c.description,
  c.published_date,
  c.cvss_v3_score,
  c.cvss_v3_severity,
  STRING_AGG(m.strike_name, ', ') as strike_profiles
FROM cverf_cve_strike_mappings m
LEFT JOIN cves c ON m.cve_id = c.id
GROUP BY m.cve_id, c.description, c.published_date, c.cvss_v3_score, c.cvss_v3_severity
ORDER BY m.cve_id
LIMIT 2500;

-- Result: 2195 rows (all Cyperf CVEs, with NVD data when available)
```

**Get last sync status:**
```sql
SELECT status, completed_at, cves_count, duration_seconds, error_message
FROM sync_metadata
WHERE job_name = 'cyperf_profiles'
ORDER BY completed_at DESC
LIMIT 1;

-- Used by StatusBar component to display "Last synced: ..."
```

---

## Data Synchronization Pipeline

### Sync Architecture

```
┌──────────────────────────────────────────────────────────┐
│         Backend Startup (main.py lifespan)               │
├──────────────────────────────────────────────────────────┤
│ 1. Initialize APScheduler                                │
│ 2. Queue immediate startup sync job                      │
│    └─ Runs asynchronously in background                 │
│ 3. Configure scheduled sync (daily at 02:00 UTC)        │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Cyperf Sync Job      │ (async)
            │ (perform_sync)       │
            └──────────┬───────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    ┌──────┐    ┌────────┐    ┌─────────────┐
    │Retry │    │Cyperf  │    │PostgreSQL   │
    │Logic │    │API     │    │(Atomic UX)  │
    │(3x)  │    │Call    │    │             │
    └──────┘    └────────┘    └─────────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ Record in sync_metadata:         │
        │ - started_at                     │
        │ - completed_at                   │
        │ - cves_count (2195)              │
        │ - duration_seconds (~30s)        │
        │ - status (success/failed)        │
        └──────────────────────────────────┘
```

### Sync Execution Timeline

```
Startup Sync (automatic):
1. API container starts
   ├─ main.py lifespan context manager runs
   ├─ APScheduler initialized
   ├─ Immediate sync job queued
   └─ API ready to serve requests (~10s)

2. Background: perform_sync() executes
   ├─ Attempt 1 (immediate)
   │  ├─ CyperfService instance created
   │  ├─ ApplicationResourcesApi.get_resources_strikes() called
   │  ├─ 2195 CVE mappings received
   │  ├─ ATOMIC: DELETE old + INSERT new
   │  └─ Duration: ~10-30s (depends on Cyperf latency)
   └─ On failure: retry Attempt 2 (immediate), then Attempt 3 (after 5s delay)

Scheduled Sync (daily):
- Trigger: 02:00 UTC (±5min jitter to prevent thundering herd)
- Same execution as startup sync
- Idempotent: safe to run multiple times
- Non-blocking: doesn't affect API request handling
```

### Sync Failure Handling

```
If Cyperf API call fails:
├─ Immediate retry (Attempt 2)
├─ If still failing: wait 5s, retry again (Attempt 3)
└─ If all 3 fail:
   ├─ Record failure in sync_metadata
   ├─ DON'T update database (retain stale data)
   ├─ Log error but don't crash scheduler
   ├─ Circuit breaker: track consecutive failures
   └─ User sees warning banner in UI (stale data notice)

NVD Rate-Limit During /cve/latest:
├─ NVD hit with 429 Too Many Requests
├─ Retry 3x with exponential backoff
├─ On all failures:
│  ├─ Serve stale Redis cache
│  ├─ Return HTTP 200 (not 500)
│  └─ Consumer gets last-known CVE data
└─ Admin notified via logs, not user-facing errors
```

### Data Consistency Guarantees

**ACID Properties:**
- **Atomicity:** Full replace transaction: `BEGIN → DELETE all → INSERT fresh → COMMIT`
  - Either all new data or all old data, never partial
- **Consistency:** Cyperf data is source of truth, NVD is supplementary
  - Missing NVD data shows as synthetic CVE record (id + strike names only)
- **Isolation:** Sync runs in separate transaction, doesn't block reads
  - Read requests get consistent snapshot at query time
- **Durability:** PostgreSQL writes to disk, survives container restarts

**Cyperf as Source of Truth:**
- `/cve/latest` queries `cverf_cve_strike_mappings` first
- LEFT JOINs to `cves` table for NVD metadata
- Result: 100% of Cyperf CVEs returned, even if NVD data missing
- "Testable" designation is purely: "does Cyperf have a strike for this CVE?"

---

## Caching Strategy

### Redis Cache Layer

**Purpose:** Reduce NVD API calls, improve search performance

**Cache Key Structure:**
```
cve:{CVE_ID}  → CVEDetail JSON object
              → TTL: 24 hours

Example:
cve:CVE-2023-26360 → {
  "id": "CVE-2023-26360",
  "description": "Adobe ColdFusion RCE...",
  "cvss_v3_score": 8.6,
  ...
}
```

**Cache Hit Rate Strategy:**
- First request for a CVE: cache MISS → fetch from NVD → write to cache + DB
- Subsequent requests: cache HIT → serve from Redis (24h)
- Stale-while-revalidate (SWR): if within 4h of expiry, serve stale + refresh background
- On cache expiry: fall back to PostgreSQL (most Cyperf CVEs have no NVD data anyway)

**Cache Warm-up:**
- Sync job populates cache with all recently-fetched NVD CVEs
- Browse page queries don't warm cache (2195 CVEs too many)
- Search page warms cache incrementally as users search

**Rate-Limit Jitter:**
```
Cache TTL: 24 hours ± 5 minutes
Purpose: Prevent "thundering herd" problem
Problem: If all cache entries expire simultaneously at 24h,
         all requests hit NVD API at same time → rate-limit
Solution: Random jitter spreads expiry across 5-minute window
```

---

## Deployment & Startup

### Full Startup Sequence

```bash
$ docker-compose up -d

[postgres] Starting...
  ├─ Initializes PostgreSQL 15
  ├─ Creates cyperf_cve_dev database
  └─ Ready in ~3s

[redis] Starting...
  ├─ Initializes Redis 7
  └─ Ready in ~1s

[api] Starting...
  ├─ Runs backend/Dockerfile
  │  ├─ FROM python:3.12-slim
  │  ├─ pip install -r requirements.txt
  │  ├─ Copy source code
  │  └─ ENTRYPOINT: uvicorn main:app
  │
  ├─ main.py lifespan() context manager runs:
  │  ├─ Redis connection pool initialized
  │  ├─ PostgreSQL connection established
  │  ├─ Alembic migrations applied
  │  │  └─ Creates cves, cverf_cve_strike_mappings, sync_metadata tables
  │  ├─ APScheduler initialized
  │  ├─ Scheduled sync job registered (02:00 UTC daily)
  │  ├─ Immediate startup sync queued
  │  └─ FastAPI app ready on :8000
  │
  ├─ Background: perform_sync() runs
  │  ├─ Connects to Cyperf controller
  │  ├─ Fetches 2195 CVE→Strike mappings
  │  ├─ Atomic: DELETE + INSERT into cverf_cve_strike_mappings
  │  └─ Duration: ~30s
  │
  └─ Health check passes (/health → 200 OK)

[nginx] (optional, production only)
  ├─ Reverse proxy for frontend + API
  └─ TLS termination

Total startup time: ~15s to fully operational
Sync job duration: ~30s (happens in background, doesn't block API)
```

### Environment Variables

```bash
# Backend (.env or docker-compose.yml)
DATABASE_URL=postgresql://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev
REDIS_URL=redis://redis:6379/0
CYPERF_CONTROLLER_IP=<IP or hostname of Cyperf controller>
CYPERF_USERNAME=<username for Cyperf SSH auth>
CYPERF_PASSWORD=<password for Cyperf SSH auth>
NVD_API_KEY=<optional NVD API key for higher rate limits>

# Frontend (.env.local)
VITE_API_URL=http://localhost:8000  # During dev (uses /api proxy)
# In production: same origin as frontend
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }
    environment:
      DATABASE_URL: postgresql://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev
      REDIS_URL: redis://redis:6379/0
      # ... other env vars
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 5s
      timeout: 2s
      retries: 3
      start_period: 10s

  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: cyperf_dev
      POSTGRES_PASSWORD: cyperf_dev_password
      POSTGRES_DB: cyperf_cve_dev
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cyperf_dev"]
      interval: 5s
      timeout: 2s
      retries: 3

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 2s
      retries: 3

volumes:
  postgres_data:
  redis_data:
```

---

## Error Handling & Resilience

### API Error Responses

**400 Bad Request**
```json
{
  "error": "INVALID_CVE_QUERY",
  "message": "Invalid CVE format: must be CVE-YYYY-NNNNN"
}
```

**404 Not Found** (exact search only)
```json
{
  "error": "CVE_NOT_FOUND",
  "message": "CVE-2024-99999 not found in NVD or local cache"
}
```

**422 Unprocessable Entity**
```json
{
  "error": "INVALID_SEVERITY",
  "message": "Severity must be: LOW | MEDIUM | HIGH | CRITICAL"
}
```

**503 Service Unavailable** (NVD exhausted, no cache)
```json
{
  "error": "NVD_UNAVAILABLE",
  "message": "NVD API rate-limited and no cached data available"
}
```

### Graceful Degradation Patterns

**When NVD API fails:**
1. Try cache (24h TTL)
2. Fall back to PostgreSQL
3. If all fail: return 503 (or 200 with empty results for browse)

**When Cyperf API fails during sync:**
1. Retry immediately
2. Retry after 5 seconds
3. If all fail: retain previous data, log error, continue scheduler
4. User sees stale-data warning banner in UI

**When PostgreSQL fails:**
1. Log error
2. Return 500 (frontend shows error page)
3. Scheduler continues (future syncs may succeed)

### Monitoring & Alerting

**Metrics to Track:**
- NVD API call latency (p50, p95, p99)
- Cache hit rate (target: >80%)
- Sync success/failure rate (target: 100%)
- Cyperf connectivity latency
- Response times by endpoint

**Logging:**
- All sync operations logged with timestamp + duration
- NVD rate-limit exhaustion logged as WARNING
- Cyperf connection failures logged as ERROR
- Circuit breaker state changes logged as INFO

---

## Performance & Scaling

### Performance Characteristics

**Browse Page (/cve/latest?limit=2500):**
- Query time: ~500-1000ms (2195 rows + LEFT JOIN + aggregation)
- Transfer size: ~5-8 MB JSON
- Frontend rendering: <100ms (React Table virtualization)

**Search Page (/cve/search):**
- Exact match (cache hit): <10ms
- Exact match (NVD query): ~500-2000ms (rate-limit dependent)
- Prefix match (SQL LIKE): ~50-200ms
- Fuzzy match (RapidFuzz): ~1000-5000ms (depends on DB size)

**Sync Job:**
- Cyperf API call: ~20-30s
- Database ATOMIC transaction: ~1-2s
- Total: ~30-40s (non-blocking, background)

### Scaling Considerations

**Current Limits:**
- 2195 CVEs ✓ (single page load)
- Single Cyperf instance ✓
- Single PostgreSQL instance ✓
- Single Redis instance ✓

**Scaling to 10,000+ CVEs:**
1. Add pagination (100 per page)
2. Add full-text search on PostgreSQL (tsvector)
3. Upgrade Redis to cluster (Sentinel for HA)
4. Read replicas for PostgreSQL (primary for writes, replicas for reads)
5. Add CDN for frontend assets

**Scaling to Multiple Cyperf Instances:**
1. Sync from each instance separately (or coordinator)
2. Merge mappings (union of strikes)
3. Store instance metadata in DB (which instance has which strikes)

---

## Key Design Decisions

### 1. Cyperf as Source of Truth

**Decision:** `/cve/latest` queries `cverf_cve_strike_mappings` first, LEFT JOINs to `cves`

**Rationale:**
- Cyperf capability is the primary concern (can we test this CVE?)
- NVD metadata is supplementary (nice-to-have context)
- Many Cyperf CVEs don't exist in modern NVD (pre-2005)
- Returning 2195 Cyperf CVEs + synthetic records for missing NVD data is better UX than "only show if NVD has it"

**Tradeoff:** Some CVEs show with minimal metadata, but this is transparent in UI

### 2. Atomic Full-Replace Sync

**Decision:** `DELETE all cverf_cve_strike_mappings; INSERT fresh` (not delta)

**Rationale:**
- Handles profile deletions correctly (delta would miss deletions)
- All-or-nothing semantics prevent partial corruption
- Simple, predictable, easy to reason about
- Cyperf data is small (~2195 rows), full refresh is fast

**Tradeoff:** Slight performance cost (~2s) vs correctness guarantee

### 3. No User-Entered Credentials

**Decision:** Cyperf credentials loaded from environment only

**Rationale:**
- Security: credentials never in database, logs, or source control
- Simplicity: no credential management UI
- Trust: Cyperf is trusted internal service (not user-facing)

**Tradeoff:** Can't support multiple Cyperf instances per deployment (future: load from config service)

### 4. Redis Cache with 24h TTL ± Jitter

**Decision:** Cache all NVD fetches for 24 hours with random ±5min jitter

**Rationale:**
- NVD rate-limit: 50 req/30s (without API key) → cache essential
- 24h is reasonable: CVE data is stable (published dates don't change)
- Jitter prevents "thundering herd": all entries expiring simultaneously
- SWR (stale-while-revalidate) at 4h: serve stale + refresh background

**Tradeoff:** Delayed visibility of NVD updates (24h lag), but acceptable for read-heavy workload

### 5. Separated Cyperf Data from NVD Data

**Decision:** Two separate tables (`cverf_cve_strike_mappings` and `cves`)

**Rationale:**
- Data ownership: NVD manages CVE metadata, Cyperf manages strike associations
- Sync independence: Cyperf sync doesn't corrupt NVD data
- Query flexibility: Can independently query "all Cyperf CVEs" vs "all NVD CVEs"
- Cyperf as INNER table, NVD as LEFT JOIN (not vice versa)

**Tradeoff:** Requires LEFT JOIN (not INNER), but semantically correct

### 6. Green Color for "Testable" Badge

**Decision:** Change from gold to green for the "Testable" label

**Rationale:**
- Visual clarity: green universally signals "go" / "yes" / "supported"
- Accessibility: green is distinct from background, passes WCAG AA
- Semantic: "this CVE is testable by Cyperf" = positive state

**Tradeoff:** Breaks consistency with gold accent color (intentional, priority on clarity)

---

## Operational Checklist

### Daily Operations

- [ ] Check API health: `GET /health` returns 200
- [ ] Verify last sync: `GET /admin/sync-status` shows recent timestamp
- [ ] Review logs for errors: `docker-compose logs api | grep -i error`
- [ ] Spot-check search: try 3-5 CVE searches
- [ ] Spot-check browse: load `/browse`, verify 2195 CVEs visible

### Weekly Operations

- [ ] Review Cyperf API connectivity (latency, errors)
- [ ] Check NVD rate-limit logs (should be infrequent)
- [ ] Verify Redis memory usage (target: <500MB)
- [ ] Verify PostgreSQL disk usage (target: <1GB)

### Monthly Operations

- [ ] Analyze search metrics: which CVEs most popular?
- [ ] Review Cyperf sync duration trend (should be stable ~30s)
- [ ] Test manual sync: `POST /admin/sync-cyperf`
- [ ] Backup PostgreSQL: `docker exec cyperf_db_dev pg_dump -U cyperf_dev cyperf_cve_dev > backup.sql`

### Disaster Recovery

**If PostgreSQL lost:**
```bash
# Recreate from backup
docker-compose down
rm -rf postgres_data
docker-compose up -d postgres redis
docker exec cyperf_api_dev alembic upgrade head
docker exec cyperf_db_dev psql -U cyperf_dev cyperf_cve_dev < backup.sql
```

**If Redis lost:**
```bash
# Redis data is supplementary (can be repopulated)
rm -rf redis_data
docker-compose restart redis
# Next NVD search will repopulate cache
```

**If Cyperf unreachable:**
- API continues to work (serves stale data)
- Sync retries 3 times (logs failures)
- UI shows stale-data warning banner
- No user-visible downtime

---

## Summary

The Cyperf CVE Tracker is a resilient, scalable system that bridges security vulnerability data (NVD) with testing capability data (Cyperf). Key architectural principles:

1. **Cyperf is source of truth** for testability
2. **NVD is supplementary** for context
3. **Redis caches** to reduce external API load
4. **Atomic syncs** prevent data corruption
5. **Graceful degradation** ensures continued operation under failure
6. **Simple data model** (3 tables) enables clear reasoning about system behavior

The application is currently production-ready for small-to-medium deployments (single Cyperf instance, <10k CVEs). Scaling guidance is provided in the Performance section.

---

**Document prepared for:** Engineering Team
**Last reviewed:** 2026-02-24
**Next review:** 2026-03-24 (or when architecture changes)
