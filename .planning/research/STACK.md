# Stack Research

**Domain:** CVE Tracker Web App with NVD API + Keysight Cyperf API Integration
**Researched:** 2026-02-22
**Confidence:** MEDIUM (Libraries are current as of Feb 2026; Cyperf wrapper version TBD against GitHub repo)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|--------------------|
| Python | 3.12+ | Backend runtime | Type hint improvements, faster performance, asyncio maturity; 3.11+ required by modern FastAPI |
| FastAPI | 0.115.x | REST API framework | Async-first, auto-generates OpenAPI docs, Pydantic v2 native, perfect for I/O-bound API work (NVD + Cyperf calls) |
| Pydantic | 2.x | Data validation / serialization | FastAPI depends on it; v2 is 5-17x faster than v1; essential for CVE schema validation |
| React | 18.x | Frontend UI framework | Component model suits search + filter + batch pattern; large ecosystem; TanStack integrations |
| Vite | 5.x | Frontend build tool | Replaces CRA; fast HMR, native ESM, minimal config; standard for new React projects 2025+ |
| SQLite (dev) / PostgreSQL 15+ (prod) | — | Persistence layer | SQLite for local dev zero-config; Postgres for production hosted deployments |
| Redis | 7.x | API response cache + rate-limit buffer | NVD API enforces rate limits (50 req/30s with key); Redis TTL-based caching is correct pattern |

### Backend Libraries — Python

| Library | Version | Purpose | When to Use |
|---------|---------|---------|----------------|
| nvdlib | 0.7.x | NVD API 2.0 Python client | Use for all NVD CVE queries; handles pagination, rate limiting headers, API key |
| cyperf-api-wrapper | latest from GitHub | Cyperf Controller API client | Mandatory per PROJECT.md; official Keysight wrapper; handles session auth |
| httpx | 0.27.x | Async HTTP client | Fallback for APIs not covered by nvdlib/cyperf-wrapper; preferred over `requests` in async FastAPI |
| SQLAlchemy | 2.x | ORM + database toolkit | Use for all DB interactions; v2 async support solid; avoids raw SQL |
| Alembic | 1.13.x | Database migration manager | Required with SQLAlchemy 2.x for schema versioning |
| APScheduler | 3.10.x | Background job scheduler | Use for daily Cyperf sync job; triggers on schedule without blocking requests |
| redis | 5.x | Redis client | Async-first; use `async with redis.Redis()` pattern in FastAPI |
| python-dotenv | 1.0.x | Environment variable loading | Use for Cyperf credentials in dev; production uses actual secrets manager |
| pydantic-settings | 2.x | Typed settings management | Reads env vars into Pydantic models; centralizes config validation at startup |
| structlog | 24.x | Structured logging | Produces JSON log output; searchable in production; prefer over stdlib logging |
| pytest | 8.x | Test framework | Standard; use with pytest-asyncio for async route testing |
| pytest-asyncio | 0.23.x | Async test support | Required for testing FastAPI async endpoints |
| httpx[test] / TestClient | — | Integration testing | FastAPI's TestClient uses httpx; use for route-level tests |

### Frontend Libraries — React/Node

| Library | Version | Purpose | When to Use |
|---------|---------|---------|----------------|
| Tailwind CSS | 3.4.x | Utility-first CSS framework | Use for all layout/styling; dark theme via `dark:` variants; enables Shodan aesthetic |
| shadcn/ui | latest | Headless component library | Copy-paste components built on Radix UI + Tailwind; avoids dependency bloat |
| Radix UI | 1.x | Accessible headless primitives | Underpins shadcn/ui; handles keyboard navigation and ARIA automatically |
| TanStack Query | 5.x | Server state management | Use for all API calls from frontend; handles caching, loading states, stale-data detection |
| TanStack Table | 8.x | Headless table logic | Use for CVE browse + batch result table; supports sorting, filtering, virtualization |
| React Router | 6.x | Client-side routing | Use for page separation: search / browse / batch import |
| Zustand | 4.x | Lightweight client state | Use ONLY for UI state (selected filters, batch input); NOT for server data |
| Axios | 1.7.x | HTTP client | Use within TanStack Query for API calls; httpx equivalent on frontend |
| react-hot-toast | 2.x | Toast notifications | Lightweight; use for batch import success/fail feedback |
| TypeScript | 5.x | JavaScript type system | Use strict mode; eliminates bugs in CVE data mapping logic |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Python package + environment management | Replaces pip + virtualenv + pyenv; significantly faster; standard in 2025 Python projects |
| Ruff | Python linter + formatter | Replaces flake8 + black + isort; extremely fast; enforce on pre-commit |
| mypy | Static type checking | Run against backend; catches Pydantic model mismatches early |
| pre-commit | Git hook manager | Enforce Ruff + mypy + secret scanning before commits |
| Docker + Docker Compose | Container runtime | Backend + Redis + optional Postgres run as stack; frontend served separately in dev |
| ESLint + Prettier | JS linter + formatter | Use with TypeScript strict mode |

---

## Installation Quick Start

```bash
# --- Backend ---
# Using uv (recommended)
uv init cvetracker-backend
uv add fastapi uvicorn[standard] pydantic pydantic-settings \
       sqlalchemy alembic httpx nvdlib \
       apscheduler python-dotenv structlog redis
# Install cyperf-api-wrapper from GitHub (no PyPI release yet)
uv add git+https://github.com/Keysight/cyperf-api-wrapper.git

# Dev dependencies
uv add --dev pytest pytest-asyncio ruff mypy pre-commit

# --- Frontend ---
npm create vite@latest cvetracker-frontend -- --template react-ts
cd cvetracker-frontend
npm install
npm install @tanstack/react-query @tanstack/react-table react-router-dom zustand react-hot-toast
npm install -D tailwindcss postcss autoprefixer typescript eslint prettier
npx shadcn@latest init
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| FastAPI | Flask | Only if team is exclusively Flask-experienced AND no async patterns needed |
| FastAPI | Django REST Framework | Only if project needs Django admin, built-in ORM migration system, AND accepts heavier footprint |
| nvdlib | Raw requests to NVD | Only if nvdlib breaks; nvdlib handles NVD API 2.0 pagination/rate-limit headers correctly |
| Redis | In-memory cache (functools.lru_cache) | Only for single-process dev; lru_cache doesn't survive restarts or horizontal scaling |
| SQLAlchemy | Tortoise ORM | Only if full async ORM without sync fallback is required; SQLAlchemy 2.x async is sufficient |
| Tailwind + shadcn/ui | Material UI (MUI) | Only if Google Material aesthetic required; MUI has heavier bundle, light-theme bias |
| Tailwind + shadcn/ui | Ant Design | Only if enterprise form/table components needed beyond Radix; similar dark-theme issues |
| TanStack Query | SWR | Either works; TanStack Query v5 has superior TS inference and mutation handling |
| Zustand | Redux Toolkit | Only if state graph becomes complex; Zustand sufficient for UI-state in search/batch tool |
| uv | pip + virtualenv | Only if team requires compatibility with older Python tooling pre-dating uv |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| requests (sync) in FastAPI async routes | Blocks event loop; defeats FastAPI concurrency for dual API calls | httpx with async/await |
| Create React App (CRA) | Officially abandoned by Facebook; slow builds; unmaintained | Vite + React |
| MUI (Material UI) default theme | Strong light-mode bias; dark theme requires major overrides; bundle ~100kb gzipped | Tailwind + shadcn/ui (dark-native) |
| Celery | Over-engineered for single scheduled job; requires message broker setup | APScheduler with Redis for state |
| In-process CVE state | NVD data too large for memory; misses updates; breaks multi-worker deployment | SQLite/Postgres + Redis cache |
| SQLite in production multi-user | Write lock contention under concurrent requests; no connection pooling | PostgreSQL 15+ with SQLAlchemy async pool |
| Axios alone (without TanStack Query) | No caching, loading states, or stale-data handling — leads to hand-rolled state | TanStack Query (uses Axios under the hood) |
| Hardcoded Cyperf credentials | Security risk; rotation requires code change | pydantic-settings + secrets manager |

---

## Stack Variants by Deployment

### Development (Single Machine)

```yaml
Backend:
  - FastAPI + Uvicorn (local dev server)
  - SQLite (zero config)
  - Redis (local Docker)
  - Cyperf Controller (demo instance or Keysight test env)

Frontend:
  - React + Vite dev server (hot reload)
  - TypeScript (strict mode)
  - Tailwind dev mode

Infrastructure:
  - docker-compose.yml with Backend + Redis + optional Postgres
  - .env for credentials (gitignored)
  - pytest for unit tests + pytest-asyncio for async tests
```

### Production (Hosted)

```yaml
Backend:
  - FastAPI + Uvicorn (behind Nginx reverse proxy)
  - PostgreSQL 15+ (managed RDS or on-prem)
  - Redis 7 (managed ElastiCache or on-prem)
  - Cyperf Controller (internal network, high availability)
  - Connection pooling: SQLAlchemy (10-20 workers), Redis (poolsize=10)

Frontend:
  - React build (static bundle, ~200kb gzipped)
  - Served by CDN or Nginx
  - TypeScript strict mode enforced

Infrastructure:
  - Docker images for backend + frontend
  - Secrets manager (Vault, AWS Secrets Manager, Azure Key Vault)
  - Monitoring: Prometheus (metrics) + Grafana (dashboards) + ELK (logs)
  - Backup: PostgreSQL automated backups + S3 snapshots
```

---

## NVD API Integration Details

- **Endpoint:** `https://services.nvd.nist.gov/rest/json/cves/2.0`
- **Rate limits:** 5 req/30s without API key; 50 req/30s with key
- **Pagination:** Max 2000 results per request; use `startIndex` to paginate
- **Response format:** JSON with CVE metadata (CVSS v3.1, v4.0, descriptions, references)
- **Key fields to extract:** id, descriptions, metrics.cvssMetricV31, published, lastModified, references
- **Caching strategy:** Redis with TTL=3600s (1h); NVD updates on schedule not immediately
- **NVD API key:** Request free at https://nvd.nist.gov/developers/request-an-api-key

### Code Pattern — NVD Query

```python
import nvdlib

# Initialize with API key (from secrets manager in production)
nvdlib_client = nvdlib.nvdlib(apiKey=KEYSIGHT_NVD_API_KEY)

# Query single CVE
cve = nvdlib_client.getCVE("CVE-2024-1234")

# Query with filters
cves = nvdlib_client.getCVE(
    keyword="chromium",
    cvssV3Severity="HIGH",
    pubStartDate="2024-01-01",
    pubEndDate="2024-12-31",
    limit=100,
    startIndex=0
)
```

---

## Cyperf API Integration Details

- **Wrapper:** `github.com/Keysight/cyperf-api-wrapper`
- **Authentication:** Username/password at client instantiation
- **Key endpoint:** Query Attack Profiles + associated CVEs
- **Response format:** JSON list of profiles with CVE associations
- **Caching:** Database cache (sqlite/postgres) updated by daily background job
- **Session handling:** Wrapper manages token lifecycle automatically

### Code Pattern — Cyperf Query

```python
from cyperf_api_wrapper import CyPerfAPI

# Initialize client (credentials from secrets manager)
cyperf = CyPerfAPI(
    ip=CYPERF_CONTROLLER_IP,
    username=KEYSIGHT_CYPERF_USERNAME,
    password=KEYSIGHT_CYPERF_PASSWORD
)

# Get all Attack Profiles + CVEs
profiles = cyperf.get_attack_profiles()  # Returns list of profile objects
cves_from_cyperf = set()
for profile in profiles:
    for cve in profile.associated_cves:
        cves_from_cyperf.add(cve.id)

# Store in database for later use
```

---

## Version Pinning

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| FastAPI 0.115.x | Pydantic 2.x | FastAPI 0.100+ dropped Pydantic v1 support |
| SQLAlchemy 2.x | Alembic 1.13.x | Alembic 1.13+ required for SQLAlchemy 2.0 async |
| pytest 8.x | pytest-asyncio 0.23.x | Use `asyncio_mode = "auto"` in pytest.ini |
| nvdlib 0.7.x | NVD API 2.0 | nvdlib 0.7+ migrated to NVD API 2.0; 0.6.x targets deprecated v1 |
| React 18.x | TanStack Query 5.x | TanStack Query v5 requires React 18 for concurrent features |
| shadcn/ui latest | Tailwind CSS 3.4.x | shadcn/ui supports Tailwind 3.4; Tailwind 4 beta also works |

---

## Deployment Checklist

- [ ] Python 3.12+ runtime selected
- [ ] uv or poetry for dependency management (frozen requirements.txt)
- [ ] FastAPI running behind Nginx/HAProxy (not exposed directly)
- [ ] PostgreSQL (prod) or SQLite (dev) database configured
- [ ] Redis configured with AUTH (prod) or localhost-only (dev)
- [ ] Secrets manager integration working (credentials NOT in code)
- [ ] NVD API key obtained and configured
- [ ] Cyperf Controller accessible and credentials verified
- [ ] SSL/TLS certificates configured (HTTPS only in prod)
- [ ] Monitoring + alerting configured (sync failures, rate limit hits, Cyperf downtime)
- [ ] Database backups automated
- [ ] Docker images built and pushed to registry
- [ ] docker-compose.yml tested locally before production deployment

---

## Cost & Performance

| Component | Baseline Cost | Performance | Notes |
|-----------|---------------|-------------|-------|
| NVD API | Free (with key) | 50 req/30s rate limit | Public API; no SLA |
| Cyperf API | Included with Cyperf license | Internal network; no public limits | Customer-hosted; no metering |
| PostgreSQL (AWS RDS) | $50-200/month | 200ms query latency | db.t3.small sufficient for MVP |
| Redis (AWS ElastiCache) | $15-50/month | <5ms latency | cache.t3.small sufficient for MVP |
| Frontend hosting (CDN) | $5-20/month | <100ms global latency | CloudFront, Cloudflare, or similar |
| Total | ~$70-270/month | Acceptable for security team tool | Scales linearly with users |

---

## Sources

- FastAPI docs: https://fastapi.tiangolo.com (HIGH confidence)
- Pydantic v2: https://docs.pydantic.dev/2.0 (HIGH confidence)
- nvdlib: Training knowledge + PyPI repo (MEDIUM confidence; verify version on install)
- cyperf-api-wrapper: GitHub Keysight/cyperf-api-wrapper (MEDIUM confidence; version TBD)
- NVD API 2.0: https://nvd.nist.gov/developers (HIGH confidence)
- React/Vite/Tailwind: Training knowledge as of Feb 2026 (MEDIUM confidence; verify at install time)
- TanStack Query v5: https://tanstack.com/query/latest (HIGH confidence)
- shadcn/ui: https://ui.shadcn.com (HIGH confidence)

---

*Stack research for: Cyperf CVE Tracker — Python FastAPI backend + React frontend*
*Researched: 2026-02-22*
