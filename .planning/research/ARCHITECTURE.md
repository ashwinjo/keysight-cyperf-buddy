# Architecture Research

**Domain:** CVE Tracker with NVD + Cyperf API Integration
**Researched:** 2026-02-22
**Confidence:** MEDIUM-HIGH (NVD API patterns well-established; Cyperf-specific patterns inferred from security tool architecture; tested against PROJECT.md constraints)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                     (React SPA, Shodan dark)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    FastAPI Backend                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Routes:                                                  │   │
│  │  /cve/search/{id}      - Single CVE lookup             │   │
│  │  /cve/latest           - Browse latest                 │   │
│  │  /cve/batch            - Import/check multiple         │   │
│  │  /sync/cyperf          - Admin: refresh Cyperf data    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                      │
│  ┌──────────────────────┬─┴─┬──────────────────────────────┐   │
│  │                      │   │                              │   │
│  ▼                      ▼   ▼                              ▼   │
│ ┌──────────────┐    ┌─────────┐   ┌──────────────────┐    │   │
│ │ NVD Client   │    │SQLAlchemy ORM   │Cyperf Client  │    │   │
│ │(nvdlib)      │    │(read/write CVE  │(cyperf-api-   │    │   │
│ │              │    │ intersection)   │wrapper)        │    │   │
│ └──────────────┘    └─────────┘   └──────────────────┘    │   │
│        │                │              │                    │   │
│        │                │              │                    │   │
│  ┌─────┴────────────────┴──────────────┴──────────────┐   │   │
│  │        Redis Cache (rate limit buffer + data)    │   │   │
│  └─────────────────────────────────────────────────────┘   │   │
└──────────────────────────────────────────────────────────────┘
                           │         │
                    ┌──────┘         └──────┐
                    │                       │
        ┌───────────▼──────────┐  ┌────────▼──────────┐
        │  NVD API              │  │ Cyperf Controller │
        │  (nvd.nist.gov)       │  │ (+ Agents)        │
        │  Rate: 50 req/30s     │  │ (+ Attack        │
        │  (with API key)       │  │  Profiles)        │
        └───────────────────────┘  └───────────────────┘
                    │
        ┌───────────▼──────────────┐
        │   SQLite (dev) /          │
        │   PostgreSQL (prod)       │
        │   - CVE data cache        │
        │   - Cyperf profile map    │
        │   - Sync state            │
        └────────────────────────────┘
```

---

## Component Boundaries

### Frontend (React SPA)

**Responsibility:** User interface, search/filter/batch entry, display results

**Key Components:**
- Search box with autocomplete (CVE-YYYY-NNNN pattern)
- Browse table with sorting, filtering by testability status
- Batch import dialog (paste CSV or text)
- Results display with Shodan-dark styling
- Export button (CSV/JSON)

**State Management:** TanStack Query for server state, Zustand for UI-only state (selected CVEs, filters)

**Communication:** REST API to backend via axios/fetch wrapped in TanStack Query

---

### Backend API (FastAPI)

**Responsibility:** Orchestrate NVD + Cyperf queries, compute intersection, serve results

**Key Endpoints:**
```python
@app.get("/cve/{cve_id}")
    # Fetch single CVE from NVD (cached) + check testability
    # Return: CVE details + testable badge

@app.get("/cve/latest")
    # Browse latest CVEs (paginated, filtered by testability)
    # Return: List of CVEs sorted by published date

@app.post("/cve/batch-check")
    # Import list of CVEs, compute bulk intersection
    # Return: Results with testable/not-testable status

@app.get("/sync/cyperf/status")
    # Check when Cyperf data was last synced
    # Return: sync timestamp + profile count

@app.post("/admin/sync-cyperf")  # Protected endpoint
    # Force immediate sync with Cyperf Controller
    # Return: sync results
```

**Process Flow:**
1. Receive request (CVE ID or list)
2. Check Redis cache first (key: `cve:{id}`, TTL: 3600s)
3. If miss: query NVD API via nvdlib
4. Check CVE against Cyperf's supported profiles (from DB cache updated by background job)
5. Compute testability (boolean: CVE exists in both NVD and Cyperf)
6. Cache result
7. Return to frontend

---

### Data Cache & Synchronization

**NVD API Cache (Redis + SQLite):**
- Redis: Fast lookup, TTL=3600s (1 hour; NVD updates infrequently)
- SQLite/PostgreSQL: Persistent store, indexed by CVE ID
- Key: `cve:{id}` → {id, cvss_v3, cvss_v4, description, published_date, references}

**Cyperf Profile Cache (SQLite/PostgreSQL):**
- Table: `cyperf_supported_cves`
- Columns: cve_id, attack_profile_name, profile_version, last_synced
- Source: Background job queries Cyperf API via cyperf-api-wrapper
- Frequency: Configurable (daily by default; immediate on admin request)
- Persistence: Survives restarts; allows offline "stale" mode if Cyperf unreachable

**Intersection Logic (In-Memory + Database):**
```python
# Pseudocode
supported_cves = cache.get_cyperf_supported_cves()  # Set<str> of CVE IDs
cve_details = cache.get_nvd_cve(cve_id)  # Dict of CVE details

def compute_testability(cve_id):
    return cve_id in supported_cves
```

---

## Data Flow

### Request Flow: Search Single CVE

```
User types CVE ID
    ↓
Frontend sends GET /cve/{id}
    ↓
Backend receives request
    ↓
Check Redis cache: cve:{id}
    ├─ Cache HIT: Return cached CVE + testability
    │
    └─ Cache MISS:
        ├─ Query NVD API (nvdlib.get_cve(id))
        ├─ Check testability (id in Cyperf set)
        ├─ Store in Redis (TTL 3600s)
        ├─ Store in SQLite (for persistence)
        └─ Return to frontend
    ↓
Frontend displays CVE details + "Can be Tested" badge
```

### Request Flow: Batch Import

```
User pastes 10 CVEs
    ↓
Frontend POST /cve/batch-check with list
    ↓
Backend receives list
    ↓
For each CVE:
    ├─ Check Redis / NVD / database (in parallel, up to 5 concurrent)
    ├─ Compute testability
    ├─ Accumulate results
    ↓
Return results list (testable + not-testable counts)
    ↓
Frontend displays results table + Export button
```

### Background Job: Sync Cyperf

```
APScheduler triggers every 24 hours (configurable)
    ↓
Cyperf client: Get all Attack Profiles + associated CVEs
    (Uses cyperf-api-wrapper with stored credentials)
    ↓
Load results into memory: Set<str> of supported CVE IDs
    ↓
Compare against current DB state
    ├─ New CVEs: Insert into cyperf_supported_cves
    ├─ Removed CVEs: Mark as deprecated
    ├─ Updated profiles: Update profile_version
    ↓
Update sync timestamp in metadata
    ↓
Clear Redis cache for Cyperf-dependent keys
    ↓
Log completion + notify admins if errors
```

---

## Project Structure

```
cvetracker/
├── backend/
│   ├── main.py                    # FastAPI app + routes
│   ├── models.py                  # Pydantic schemas (CVE, TestabilityResult)
│   ├── database.py                # SQLAlchemy session + models
│   ├── services/
│   │   ├── nvd_service.py         # NVD API integration (nvdlib wrapper)
│   │   ├── cyperf_service.py      # Cyperf API integration (cyperf-api-wrapper)
│   │   ├── cache_service.py       # Redis + database caching logic
│   │   └── sync_service.py        # Background sync job logic
│   ├── routes/
│   │   ├── cve.py                 # GET /cve/{id}, GET /cve/latest, POST /cve/batch-check
│   │   ├── sync.py                # GET /sync/status, POST /sync/cyperf (admin)
│   │   └── health.py              # GET /health for monitoring
│   ├── migrations/                # Alembic migration files
│   ├── tests/                     # pytest test suite
│   └── requirements.txt           # Dependencies
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # React entry point
│   │   ├── App.tsx                # Router + layout
│   │   ├── pages/
│   │   │   ├── SearchPage.tsx     # Search + details view
│   │   │   ├── BrowsePage.tsx     # Latest + filter
│   │   │   └── BatchPage.tsx      # Import + results
│   │   ├── components/
│   │   │   ├── CVETable.tsx       # Reusable table for results
│   │   │   ├── TestabilityBadge.tsx
│   │   │   └── ExportButton.tsx
│   │   ├── hooks/
│   │   │   ├── useCVESearch.ts    # TanStack Query wrapper for /cve/{id}
│   │   │   ├── useCVEBatch.ts     # Wrapper for batch-check
│   │   │   └── useCVELatest.ts    # Wrapper for browse
│   │   └── styles/                # Tailwind + shadcn/ui config (dark theme)
│   ├── tailwind.config.ts         # Shodan-like dark palette
│   ├── tsconfig.json
│   └── package.json
├── docker-compose.yml             # Backend + Redis + optional Postgres
├── .env.example
└── README.md
```

---

## Key Design Patterns

### Pattern 1: Service Layer Abstraction

**What:** Separate NVD/Cyperf integration logic from FastAPI routes

**Why:** Testable (mock services for unit tests), reusable (CLI tools can reuse services), maintainable

**Example:**
```python
# services/nvd_service.py
class NVDService:
    def get_cve(self, cve_id: str) -> Optional[CVEDetails]:
        # Logic: check cache, query API, store in DB
        pass

# routes/cve.py
@app.get("/cve/{cve_id}")
async def get_cve(cve_id: str, nvd: NVDService = Depends()):
    return nvd.get_cve(cve_id)
```

### Pattern 2: Cache-Aside (Lazy Loading)

**What:** Check cache first; if miss, fetch from API + populate cache

**Why:** Balances freshness with rate-limit compliance; 99% hit rate after initial load

**Where:** NVD API queries (high cardinality, infrequent changes)

### Pattern 3: Background Job + Eventual Consistency

**What:** Cyperf data syncs asynchronously every 24h; frontend sees "last synced X hours ago"

**Why:** Cyperf queries may be slow/unreliable; don't block user requests on external API

**Trade-off:** 24h stale data is acceptable (CVE->Attack Profile mappings change infrequently)

### Pattern 4: TanStack Query for Server State

**What:** Frontend treats backend API as single source of truth; Query handles caching, refetch, stale-while-revalidate

**Why:** Eliminates manual state management; automatic stale-data detection; reduces network requests

---

## Data Flow Diagrams

### Component Communication

```
Frontend
  ├── (TanStack Query)
  │    └─→ Axios call → Backend API
  │         ↓
  │    Backend fetches / caches
  │         ↓
  │    Response with testability badge
  │         ↓
  │    TanStack Query caches response
  │         ↓
  │    Component re-renders
  │
  └── (Zustand)
       └─→ Local UI state (selected filters, batch input)
```

### API Integration Points

```
Backend Services
  ├─ NVD Service
  │   ├─ Uses: nvdlib client
  │   ├─ Calls: NVD REST API (https://services.nvd.nist.gov/rest/json/cves/2.0)
  │   ├─ Rate limit: 50 req/30s (with API key)
  │   ├─ Cache: Redis + SQLite
  │   └─ Timeout: 10s per request
  │
  ├─ Cyperf Service
  │   ├─ Uses: cyperf-api-wrapper (Python SDK)
  │   ├─ Auth: Username/password (from secrets manager)
  │   ├─ Calls: Cyperf Controller API (internal, no rate limit)
  │   ├─ Data: Attack Profiles + associated CVEs
  │   └─ Sync frequency: Daily (background job)
  │
  └─ Cache Service
      ├─ Redis: Session cache, rate-limit buffer (5min TTL for sync state)
      ├─ SQLite/Postgres: Persistent CVE data + Cyperf mapping
      └─ Strategy: Invalidate Cyperf cache after sync job completes
```

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 users | Monolith (FastAPI + SQLite + Redis) on single VM; daily Cyperf sync |
| 100-1k users | Add read replicas for DB if write pattern emerges; background job stays on primary |
| 1k-10k users | Migrate to PostgreSQL; add connection pooling (pgBouncer); split write/read paths if needed |
| 10k+ users | Microservices: separate NVD sync service, Cyperf sync service, query API |

### First Bottleneck: NVD API Rate Limit

**Symptom:** "Rate limited by NVD" errors after ~50 searches in 30 seconds

**How to Fix:**
1. Request NVD API key (increases limit 10x to 50 req/30s)
2. Implement queue for burst traffic (Celery + Redis)
3. Increase Redis TTL from 1h to 24h (NVD data changes slowly)
4. Pre-populate top 1000 CVEs weekly via background job

### Second Bottleneck: Cyperf Controller Availability

**Symptom:** "Cyperf unreachable" errors; user can't verify testability

**How to Fix:**
1. Cache last-known Cyperf state in DB; serve stale with timestamp
2. Display warning banner: "Cyperf data is X hours old"
3. Add Cyperf health check; retry with exponential backoff
4. Consider failover to secondary Cyperf Controller (enterprise deployments)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous NVD Calls in Request Path

**What people do:** Call NVD API for every search (no caching)

**Why it's wrong:**
- Rate-limited immediately
- User waits 2-5s per search (bad UX)
- Wastes bandwidth on repeated queries

**Do this instead:** Cache in Redis + SQLite with 1h TTL; background refresh

### Anti-Pattern 2: Hardcoded Cyperf Credentials in Code

**What people do:** Store username/password in `.env` or config file

**Why it's wrong:**
- Credentials leak in git history
- Can't rotate without redeploying
- Not suitable for multi-team use

**Do this instead:** Secrets manager (Vault, AWS Secrets Manager) with IAM controls

### Anti-Pattern 3: Querying Cyperf on Every Request

**What people do:** Call Cyperf API for every testability check

**Why it's wrong:**
- Cyperf Controller may be slow or unreachable
- Blocks user requests on external availability
- No cache invalidation strategy

**Do this instead:** Background job (24h sync) + in-memory cache + eventual consistency model

### Anti-Pattern 4: Single Database for Dev/Prod

**What people do:** Deploy same SQLite to production

**Why it's wrong:**
- No connection pooling
- Write lock contention under concurrent load
- No HA or replication

**Do this instead:** PostgreSQL in production; SQLite for local dev only

---

## Integration Points

### External Services

| Service | Integration Pattern | Rate Limits | Error Handling |
|---------|---------------------|-------------|-----------------|
| NVD API | nvdlib (sync HTTP client) | 50 req/30s | Retry with exponential backoff; serve stale cache on 429 |
| Cyperf API | cyperf-api-wrapper (Python SDK) | None (internal) | Fall back to cached state; log error + alert ops |
| Redis | Direct async connection | None (local) | Fall back to DB if Redis down; service degrades gracefully |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Frontend ↔ Backend | REST API (JSON) | Versioning strategy for breaking changes |
| Backend ↔ NVD Service | Dependency injection | Service is singleton; reused across requests |
| Backend ↔ Cyperf Service | Dependency injection + background job | Decoupled: requests don't wait for sync |
| Backend ↔ Cache | Dependency injection | Abstraction allows swapping Redis for in-memory cache in tests |

---

## Sources

- NVD API v2.0: Public documentation at nvd.nist.gov/developers (HIGH confidence)
- Cyperf architecture: Keysight public documentation (MEDIUM confidence; wrapper details unverified)
- FastAPI/SQLAlchemy patterns: Production-standard patterns (HIGH confidence)
- Rate limiting/caching strategies: Industry best practices (HIGH confidence)

---

*Architecture research for: Cyperf CVE Tracker*
*Researched: 2026-02-22*
