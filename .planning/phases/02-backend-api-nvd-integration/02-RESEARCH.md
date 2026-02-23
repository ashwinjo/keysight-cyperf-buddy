# Phase 2 Research: Backend API + NVD Integration

**Phase:** 02-backend-api-nvd-integration
**Researched:** 2026-02-23
**Requirements covered:** SEARCH-01, SEARCH-02, SEARCH-05, BROWSE-01, BROWSE-02, BROWSE-04, SYNC-01, SYNC-05

---

## Table of Contents

1. [NVD API Integration Patterns](#1-nvd-api-integration-patterns)
2. [Redis Caching Strategies in FastAPI](#2-redis-caching-strategies-in-fastapi)
3. [Fuzzy Search Implementation](#3-fuzzy-search-implementation)
4. [Rate-Limit Handling and Circuit Breaker Patterns](#4-rate-limit-handling-and-circuit-breaker-patterns)
5. [Response Serialization and Pydantic Models](#5-response-serialization-and-pydantic-models)
6. [Architectural Decisions Summary](#6-architectural-decisions-summary)

---

## 1. NVD API Integration Patterns

### 1.1 nvdlib Overview

`nvdlib` (v0.7.x+) is the chosen abstraction over the NVD API 2.0 REST endpoint (`https://services.nvd.nist.gov/rest/json/cves/2.0`). As of v0.7, `getCVE()` is removed; the unified entry point is `searchCVE()`.

**Key limitation: nvdlib is synchronous.** It uses the `requests` library internally. Running it directly in a FastAPI async route blocks the event loop. The mitigation is wrapping it in `asyncio.to_thread()` (Python 3.9+) to push it to a thread pool.

### 1.2 searchCVE Function Signature

```python
import nvdlib

results: list = nvdlib.searchCVE(
    cveId=None,           # Exact CVE ID, e.g. "CVE-2024-1234"
    cpeName=None,         # CPE filter
    keywordSearch=None,   # Full-text keyword filter
    keywordExactMatch=False,
    pubStartDate=None,    # "YYYY-MM-DD HH:MM" format; max 120-day range
    pubEndDate=None,
    cvssV3Severity=None,  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    sourceIdentifier=None,
    isVulnerable=False,
    limit=None,           # Max results to return (library-level cap)
    key=None,             # NVD API key string
    delay=None,           # Seconds between requests; >= 0.6 with key
)
```

**Rate limits:**
- Without API key: 10 requests/minute (6s enforced sleep between calls)
- With API key: 100 requests/minute (0.6s minimum delay)

**Note on `cvssV4Severity`:** The NVD REST API 2.0 accepts `cvssV4Severity` as a query parameter, but nvdlib (as of 0.7.x) does not expose it as a named argument in `searchCVE()`. For v4.0 severity filtering, two options exist:
1. Call the NVD REST API directly via `httpx` with `cvssV4Severity` parameter.
2. Use nvdlib for the data fetch and post-filter in Python based on the `v40severity` attribute.

Post-filtering in Python is the safer approach because it avoids maintaining a secondary HTTP client pattern and the filtering overhead is negligible for typical response sizes.

### 1.3 CVE Object Attributes

The returned objects expose these attributes (check for `None` before using — not all CVEs have all CVSS versions):

```python
cve = nvdlib.searchCVE(cveId="CVE-2021-26855")[0]

# Core identity
cve.id              # "CVE-2021-26855"
cve.published       # "2021-03-03T01:15:00.000" (ISO 8601 string)
cve.lastModified    # "2024-11-21T23:15:00.000"
cve.vulnStatus      # "Modified" | "Analyzed" | "Awaiting Analysis"

# English description
cve.descriptions[0].value   # Description text (lang == "en")

# CVSS v3.1
cve.v31score        # float, e.g. 9.8
cve.v31severity     # "CRITICAL"
cve.v31vector       # "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

# CVSS v3.0 (older CVEs may have this instead of v3.1)
cve.v30score
cve.v30severity
cve.v30vector

# CVSS v4.0 (recent CVEs only; nvdlib >= 0.7.6)
cve.v40score
cve.v40severity
cve.v40vector

# References: list of objects with .url attribute
[ref.url for ref in cve.references]   # ["https://...", ...]
```

### 1.4 Async Wrapping Pattern

Because nvdlib is synchronous, wrap all calls with `asyncio.to_thread` to prevent event loop blocking:

```python
import asyncio
import nvdlib
from typing import Optional


class NVDClient:
    """Thread-safe async wrapper around nvdlib."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
        # With API key: 0.6s delay minimum; without: nvdlib enforces 6s
        self._delay: float = 0.6 if api_key else 6.0

    async def fetch_cve(self, cve_id: str) -> Optional[object]:
        """Fetch a single CVE by exact ID. Returns nvdlib CVE object or None."""
        def _sync_fetch() -> list:
            return nvdlib.searchCVE(
                cveId=cve_id,
                key=self._api_key,
                delay=self._delay,
            )

        results = await asyncio.to_thread(_sync_fetch)
        return results[0] if results else None

    async def fetch_latest(
        self,
        pub_start: str,
        pub_end: str,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Fetch latest CVEs with optional severity filter."""
        def _sync_fetch() -> list:
            return nvdlib.searchCVE(
                pubStartDate=pub_start,
                pubEndDate=pub_end,
                cvssV3Severity=severity.upper() if severity else None,
                limit=limit,
                key=self._api_key,
                delay=self._delay,
            )

        return await asyncio.to_thread(_sync_fetch)
```

### 1.5 Pagination Strategy for /cve/latest

NVD API paginates via `startIndex` + `resultsPerPage` (max 2000 per call). For the `/cve/latest` endpoint, the approach is:

1. Query NVD for CVEs published in the last N days (default: 30 days)
2. Page through results using nvdlib's internal pagination (it handles this automatically when `limit` is set)
3. Cache each CVE individually in Redis (`cve:{id}`) as they are fetched
4. Store results in the `cves` database table for persistence

**Date window logic:**

```python
from datetime import datetime, timedelta, timezone


def get_date_window(days: int = 30) -> tuple[str, str]:
    """Return (start, end) date strings for NVD pubStartDate/pubEndDate."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return (
        start.strftime("%Y-%m-%d %H:%M"),
        now.strftime("%Y-%m-%d %H:%M"),
    )
```

**Pagination note:** nvdlib's `limit` parameter is a library-level cap, not the NVD `resultsPerPage`. For large date windows, use `searchCVE_V2()` (generator) to avoid loading thousands of CVEs into memory.

---

## 2. Redis Caching Strategies in FastAPI

### 2.1 Async Redis Connection

Use `redis[asyncio]` v5.x (already in requirements.txt). Create a singleton connection pool managed by the FastAPI lifespan context:

```python
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI


redis_client: aioredis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = await aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    yield
    await redis_client.aclose()
```

Inject via FastAPI dependency:

```python
from fastapi import Depends


async def get_redis() -> aioredis.Redis:
    """Dependency: returns the shared Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client
```

### 2.2 Cache Key Design

Use a structured, versioned key scheme with colon separators:

```
cve:v1:{CVE_ID}          # Individual CVE record (24h TTL)
cve:v1:latest:{hash}     # Latest CVE list page (NOT cached per decision)
```

**Key design rules:**
- Prefix with `cve:v1:` to enable bulk invalidation and future schema versioning
- CVE ID is always uppercase-normalized (e.g., `CVE-2024-1234`, never `cve-2024-1234`)
- No cache metadata (no `cached_at` or TTL values) in the stored value per context decisions

```python
def make_cve_cache_key(cve_id: str) -> str:
    return f"cve:v1:{cve_id.upper()}"
```

### 2.3 TTL Management

**Decision from context:** 24+ hour TTL per CVE record. NVD updates infrequently.

```python
CVE_TTL_SECONDS = 86400  # 24 hours base TTL
CVE_TTL_JITTER_SECONDS = 3600  # +/- 1 hour jitter to prevent thundering herd
```

Apply jitter to prevent cache stampede (all keys expiring simultaneously after bulk load):

```python
import random


def cvs_ttl_with_jitter() -> int:
    """Returns TTL between 23h and 25h to spread cache expiry."""
    return CVE_TTL_SECONDS + random.randint(
        -CVE_TTL_JITTER_SECONDS, CVE_TTL_JITTER_SECONDS
    )
```

### 2.4 Cache Read/Write Pattern (Cache-Aside)

```python
import json
from typing import Optional


class CVECacheService:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, cve_id: str) -> Optional[dict]:
        """Return cached CVE dict or None on miss."""
        key = make_cve_cache_key(cve_id)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, cve_id: str, data: dict) -> None:
        """Store CVE dict in Redis with TTL."""
        key = make_cve_cache_key(cve_id)
        serialized = json.dumps(data, default=str)  # default=str handles datetime
        await self._redis.set(key, serialized, ex=cvs_ttl_with_jitter())

    async def get_remaining_ttl(self, cve_id: str) -> int:
        """Returns remaining TTL in seconds; -2 if key does not exist."""
        key = make_cve_cache_key(cve_id)
        return await self._redis.ttl(key)

    async def exists(self, cve_id: str) -> bool:
        key = make_cve_cache_key(cve_id)
        return bool(await self._redis.exists(key))
```

### 2.5 Stale-While-Revalidate Pattern

**Decision from context:** Proactively refresh popular CVEs before TTL expiry.

**Trigger condition:** If a CVE is accessed and its remaining TTL is below a threshold (e.g., under 4 hours of a 24h window), enqueue a background refresh without blocking the current request.

```python
from fastapi import BackgroundTasks

REFRESH_THRESHOLD_SECONDS = 4 * 3600  # Refresh if < 4 hours remaining


async def get_cve_with_swr(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> Optional[dict]:
    """
    Cache-aside with stale-while-revalidate.
    Returns cached data immediately; triggers background refresh if near expiry.
    """
    cached = await cache.get(cve_id)

    if cached is not None:
        remaining_ttl = await cache.get_remaining_ttl(cve_id)
        if remaining_ttl < REFRESH_THRESHOLD_SECONDS:
            # Serve stale data now; refresh in background
            background_tasks.add_task(
                _refresh_cve_in_background, cve_id, cache, nvd, db
            )
        return cached

    # Cache miss: fetch from NVD synchronously (in this request)
    return await _fetch_and_cache_cve(cve_id, cache, nvd, db)


async def _refresh_cve_in_background(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
) -> None:
    """Background task: refresh CVE data from NVD without blocking request."""
    try:
        await _fetch_and_cache_cve(cve_id, cache, nvd, db)
    except Exception:
        # Background refresh failure is non-fatal; stale data continues serving
        pass
```

**Trade-off:** FastAPI `BackgroundTasks` run in the same process after the response is sent. They do not survive server restarts. For higher-reliability refresh scheduling, use APScheduler or ARQ. For this phase, `BackgroundTasks` is sufficient.

### 2.6 Redis Failure Handling

Redis down must not bring down the API. Wrap all Redis calls in try/except and fall back to direct NVD fetch:

```python
async def get_cve_with_fallback(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
) -> Optional[dict]:
    try:
        cached = await cache.get(cve_id)
        if cached is not None:
            return cached
    except Exception:
        pass  # Redis unavailable; continue to NVD

    return await _fetch_and_cache_cve(cve_id, cache, nvd, db)
```

---

## 3. Fuzzy Search Implementation

### 3.1 CVE ID Search Characteristics

CVE IDs have a deterministic structure: `CVE-YYYY-NNNNN`. This means:

- **Exact match** is the primary and most common case
- **Prefix/wildcard match** covers patterns like `CVE-2024-*` or `CVE-2024-123*`
- **Full fuzzy match** (Levenshtein distance) handles typos like `CVE-20244-1234`

The cardinality issue: NVD contains 250,000+ CVEs. Full in-memory fuzzy scan on every request is not viable. The solution is a two-tier approach.

### 3.2 Search Tiers

**Tier 1: Exact Match (Redis + DB)**

For `GET /cve/search?id=CVE-2024-1234`:
1. Normalize input: uppercase, strip whitespace
2. Check Redis cache (`cve:v1:CVE-2024-1234`)
3. If miss: query NVD with `cveId=CVE-2024-1234` (exact ID lookup)
4. Cache and return

This covers SEARCH-01 (exact ID search). Response time: <10ms on cache hit, ~1-3s on NVD miss.

**Tier 2: Prefix/Wildcard Match (DB Query)**

For `GET /cve/search?id=CVE-2024-*`:
1. Detect wildcard (`*` or `%` in query string)
2. Translate to SQL `LIKE` or PostgreSQL `ILIKE` query against `cves.id`
3. Return up to 50 matching results from DB (no NVD query — only DB-cached CVEs)

```python
import re


def parse_search_query(query: str) -> tuple[str, bool]:
    """
    Returns (normalized_query, is_wildcard).
    Wildcards: * or trailing partial (e.g., CVE-2024-1)
    """
    normalized = query.upper().strip()
    is_wildcard = "*" in normalized or not bool(
        re.fullmatch(r"CVE-\d{4}-\d+", normalized)
    )
    return normalized, is_wildcard


async def search_cves_by_prefix(
    query: str,
    db: AsyncSession,
    limit: int = 50,
) -> list:
    """SQL LIKE search against cached CVE IDs."""
    sql_pattern = query.replace("*", "%")
    stmt = (
        select(CVE)
        .where(CVE.id.like(sql_pattern))
        .order_by(CVE.published_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

**Tier 3: Fuzzy Match (RapidFuzz, bounded scope)**

Fuzzy matching is applied only when:
- The query does not match the exact CVE pattern
- The query is not a wildcard
- The DB prefix search returns zero results

This bounds the fuzzy candidate set to CVEs already in the local DB (not all 250k NVD CVEs), keeping it performant.

```python
from rapidfuzz import fuzz, process


async def fuzzy_search_cve_ids(
    query: str,
    db: AsyncSession,
    score_cutoff: float = 80.0,
    limit: int = 10,
) -> list[str]:
    """
    Fuzzy match query against CVE IDs in the local database.
    Returns top N matching CVE IDs sorted by similarity score.
    """
    # Fetch all CVE IDs from DB (only the ID column, not full records)
    stmt = select(CVE.id)
    result = await db.execute(stmt)
    all_ids: list[str] = result.scalars().all()

    matches = process.extract(
        query.upper(),
        all_ids,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=score_cutoff,
        limit=limit,
    )
    return [match[0] for match in matches]
```

**Performance note:** RapidFuzz is implemented in C++ and handles ~1M string comparisons/second. With 50k locally-cached CVE IDs, a fuzzy scan takes ~50ms, acceptable for a non-primary path.

**Decision: Do not run fuzzy match against NVD live.** Only fuzzy-match against locally cached CVE IDs. If the CVE is not in the local cache, the user must provide the exact ID.

### 3.3 Search Dispatch Logic

```python
async def dispatch_cve_search(
    query: str,
    severity: Optional[str],
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> list[dict]:
    """
    Routes to exact, prefix, or fuzzy search based on query shape.
    Always applies severity post-filter if requested.
    """
    normalized, is_wildcard = parse_search_query(query)

    if re.fullmatch(r"CVE-\d{4}-\d+", normalized):
        # Tier 1: Exact CVE ID
        result = await get_cve_with_swr(
            normalized, cache, nvd, background_tasks, db
        )
        results = [result] if result else []

    elif is_wildcard:
        # Tier 2: Prefix/wildcard from DB
        db_cves = await search_cves_by_prefix(normalized, db)
        results = [cve_to_dict(c) for c in db_cves]

    else:
        # Tier 3: Fuzzy (typo correction)
        fuzzy_ids = await fuzzy_search_cve_ids(normalized, db)
        results = []
        for cve_id in fuzzy_ids:
            cve = await get_cve_with_swr(
                cve_id, cache, nvd, background_tasks, db
            )
            if cve:
                results.append(cve)

    # Apply severity filter (CVSS v3.1 OR v4.0 match)
    if severity:
        results = filter_by_severity(results, severity.upper())

    return results


def filter_by_severity(cves: list[dict], severity: str) -> list[dict]:
    """
    Returns CVEs where cvss_v3_severity OR cvss_v4_severity matches.
    Case-insensitive. Per CONTEXT.md decision.
    """
    return [
        c for c in cves
        if (c.get("cvss_v3_severity") or "").upper() == severity
        or (c.get("cvss_v4_severity") or "").upper() == severity
    ]
```

---

## 4. Rate-Limit Handling and Circuit Breaker Patterns

### 4.1 NVD Rate-Limit Behavior

NVD returns HTTP 429 when the rate limit is exceeded. The `Retry-After` header is not always present. nvdlib internally sleeps between requests (6s without key, 0.6s with key), so thundering-herd 429s occur primarily when:
1. Multiple concurrent FastAPI workers share no coordination
2. The NVD API key is missing and background jobs run alongside user requests

### 4.2 Retry Strategy with Tenacity

Use `tenacity` for retry logic around NVD calls. The key insight: retry `asyncio.to_thread(nvdlib.searchCVE)` calls, not individual nvdlib internals.

```python
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    before_sleep_log,
)
import logging
import httpx

logger = logging.getLogger(__name__)


class NVDRateLimitError(Exception):
    """Raised when NVD returns 429."""
    pass


@retry(
    retry=retry_if_exception_type(NVDRateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_cve_with_retry(nvd: NVDClient, cve_id: str) -> Optional[object]:
    """
    Fetches CVE from NVD with exponential backoff on 429.
    Raises NVDRateLimitError after 3 attempts to allow caller to serve cache.
    """
    try:
        return await nvd.fetch_cve(cve_id)
    except Exception as exc:
        # nvdlib raises exceptions for HTTP errors; inspect message for 429
        if "403" in str(exc) or "429" in str(exc) or "rate" in str(exc).lower():
            raise NVDRateLimitError(f"NVD rate limited for {cve_id}") from exc
        raise
```

**Retry configuration rationale:**
- `wait_exponential(min=2, max=30)`: 2s, 4s, 8s (capped at 30s)
- `+ wait_random(0, 2)`: Jitter to prevent synchronized retries across workers
- `stop_after_attempt(3)`: Fail fast after 3 attempts; don't queue indefinitely
- `reraise=True`: Re-raise `NVDRateLimitError` so caller can fall back to cache

### 4.3 Rate-Limit Fallback: Serve Cache on 429 (SYNC-05)

This is the critical requirement: when NVD is rate-limited, serve cached data with HTTP 200, not HTTP 500.

```python
async def get_cve_resilient(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> tuple[Optional[dict], bool]:
    """
    Returns (cve_data, served_from_cache).
    On NVD rate-limit: returns cached data if available, else None.
    Never raises NVDRateLimitError to the caller.
    """
    # Always check cache first
    cached = await cache.get(cve_id)
    if cached is not None:
        remaining_ttl = await cache.get_remaining_ttl(cve_id)
        if remaining_ttl < REFRESH_THRESHOLD_SECONDS:
            background_tasks.add_task(
                _refresh_cve_in_background, cve_id, cache, nvd, db
            )
        return cached, True

    # Cache miss: try NVD with retries
    try:
        nvd_obj = await fetch_cve_with_retry(nvd, cve_id)
        if nvd_obj is None:
            return None, False
        cve_data = extract_cve_fields(nvd_obj)
        await cache.set(cve_id, cve_data)
        await upsert_cve_to_db(cve_data, db)
        return cve_data, False

    except NVDRateLimitError:
        # Exhausted retries. Check DB as last resort.
        db_cve = await get_cve_from_db(cve_id, db)
        if db_cve:
            return cve_to_dict(db_cve), True
        # No cached data anywhere; return None — route will return 404 or 503
        return None, False
```

**Route layer behavior:**

```python
@router.get("/search")
async def search_cve(
    id: str = Query(..., description="CVE ID to search"),
    severity: Optional[str] = Query(None),
    cache: CVECacheService = Depends(get_cache_service),
    nvd: NVDClient = Depends(get_nvd_client),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> CVESearchResponse:
    data, from_cache = await get_cve_resilient(
        id, cache, nvd, db, background_tasks
    )
    if data is None:
        # NVD unreachable AND no cache exists for this CVE
        raise HTTPException(
            status_code=503,
            detail="CVE data unavailable: NVD API unreachable and no cached data exists",
        )
    return CVESearchResponse(**data)
    # Note: HTTP 200 in all cases where data is available, regardless of source
```

### 4.4 Circuit Breaker Pattern

For production resilience, a circuit breaker prevents sending requests to a known-down NVD API. Use `aiobreaker` (async-native fork of pybreaker):

```python
from aiobreaker import CircuitBreaker, CircuitBreakerError


nvd_circuit_breaker = CircuitBreaker(
    fail_max=5,          # Trip after 5 consecutive failures
    timeout_duration=60, # Reset to half-open after 60 seconds
)


async def fetch_cve_circuit_guarded(nvd: NVDClient, cve_id: str) -> Optional[object]:
    """
    Wraps NVD fetch in a circuit breaker.
    In OPEN state, raises CircuitBreakerError immediately without contacting NVD.
    """
    try:
        return await nvd_circuit_breaker.call_async(fetch_cve_with_retry, nvd, cve_id)
    except CircuitBreakerError:
        # Circuit is OPEN: NVD is known-down, skip to cache fallback
        raise NVDRateLimitError("Circuit open: NVD API unavailable")
```

**State machine:**
- `CLOSED`: All requests flow normally
- `OPEN`: After 5 consecutive failures, all requests fail immediately for 60s
- `HALF-OPEN`: After 60s, allows one test request; if successful, returns to CLOSED

**Decision:** Circuit breaker is a production hardening concern. For Phase 2, implement tenacity retry + cache fallback as the primary resilience mechanism. Circuit breaker is recommended but can be added as a follow-on without changing the API contract.

---

## 5. Response Serialization and Pydantic Models

### 5.1 CVE Response Schema (Flattened)

Per context decisions: flattened JSON, no nested objects, curated field set.

```python
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Optional


class CVEDetail(BaseModel):
    """
    Single CVE record — flattened, curated field set.
    Covers SEARCH-02 and BROWSE-04 requirements.
    """
    model_config = {"from_attributes": True}

    # Identity
    id: str = Field(..., description="CVE identifier (e.g. CVE-2024-1234)")
    description: str = Field(
        default="No description available",
        description="English description from NVD",
    )
    published_date: Optional[datetime] = Field(
        None, description="Date CVE was published in NVD (UTC)"
    )

    # CVSS v3.1
    cvss_v3_score: Optional[float] = Field(
        None, description="CVSS v3.1 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v3_severity: Optional[str] = Field(
        None, description="CVSS v3.1 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v3_vector: Optional[str] = Field(
        None, description="CVSS v3.1 vector string"
    )

    # CVSS v4.0
    cvss_v4_score: Optional[float] = Field(
        None, description="CVSS v4.0 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v4_severity: Optional[str] = Field(
        None, description="CVSS v4.0 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v4_vector: Optional[str] = Field(
        None, description="CVSS v4.0 vector string"
    )

    # References
    reference_urls: list[str] = Field(
        default_factory=list,
        description="List of reference URLs from NVD",
    )

    @field_serializer("published_date")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO 8601 string for JSON responses."""
        return dt.isoformat() if dt else None
```

**Design notes:**
- `float` not `Decimal` for CVSS scores: Pydantic v2 serializes `Decimal` as strings in JSON, which breaks frontend numeric comparisons. Use `float` with `ge`/`le` bounds.
- `reference_urls: list[str]` not `references: str` (the DB column stores JSON-encoded string); the service layer deserializes before building this model.
- `description` has a default rather than `Optional[str]` because every valid NVD CVE has at least one description.

### 5.2 Search Response (wraps list with pagination metadata)

```python
class CVESearchResponse(BaseModel):
    """Response for /cve/search."""
    results: list[CVEDetail]
    total: int = Field(..., description="Total number of matching CVEs")
    query: str = Field(..., description="Normalized query that was executed")


class CVELatestResponse(BaseModel):
    """Response for /cve/latest."""
    results: list[CVEDetail]
    total: int = Field(..., description="Number of CVEs in this page")
    page: int = Field(1, description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of results per page")
    severity_filter: Optional[str] = Field(
        None, description="Applied severity filter if any"
    )
```

### 5.3 NVD Object to Dict Mapping

Extract fields from nvdlib's CVE object into a plain dict for caching. This is the single point where nvdlib's attribute names are translated to the application's schema:

```python
import json
from datetime import datetime


def extract_cve_fields(nvd_cve: object) -> dict:
    """
    Maps nvdlib CVE object attributes to application schema dict.
    Safe for all NVD CVEs regardless of CVSS version availability.
    """
    # Extract English description
    description = "No description available"
    if hasattr(nvd_cve, "descriptions") and nvd_cve.descriptions:
        for desc in nvd_cve.descriptions:
            if getattr(desc, "lang", "") == "en":
                description = desc.value
                break

    # Parse published date (ISO 8601 string from nvdlib)
    published_date = None
    if hasattr(nvd_cve, "published") and nvd_cve.published:
        try:
            published_date = datetime.fromisoformat(
                nvd_cve.published.rstrip("Z")
            ).isoformat()
        except ValueError:
            published_date = None

    # Extract references
    reference_urls: list[str] = []
    if hasattr(nvd_cve, "references") and nvd_cve.references:
        reference_urls = [
            ref.url for ref in nvd_cve.references
            if hasattr(ref, "url") and ref.url
        ]

    # CVSS v3.1 (prefer v31 over v30)
    cvss_v3_score = getattr(nvd_cve, "v31score", None) or getattr(nvd_cve, "v30score", None)
    cvss_v3_severity = (
        getattr(nvd_cve, "v31severity", None) or getattr(nvd_cve, "v30severity", None)
    )
    cvss_v3_vector = (
        getattr(nvd_cve, "v31vector", None) or getattr(nvd_cve, "v30vector", None)
    )

    # CVSS v4.0
    cvss_v4_score = getattr(nvd_cve, "v40score", None)
    cvss_v4_severity = getattr(nvd_cve, "v40severity", None)
    cvss_v4_vector = getattr(nvd_cve, "v40vector", None)

    return {
        "id": nvd_cve.id,
        "description": description,
        "published_date": published_date,
        "cvss_v3_score": float(cvss_v3_score) if cvss_v3_score is not None else None,
        "cvss_v3_severity": cvss_v3_severity.upper() if cvss_v3_severity else None,
        "cvss_v3_vector": cvss_v3_vector,
        "cvss_v4_score": float(cvss_v4_score) if cvss_v4_score is not None else None,
        "cvss_v4_severity": cvss_v4_severity.upper() if cvss_v4_severity else None,
        "cvss_v4_vector": cvss_v4_vector,
        "reference_urls": reference_urls,
    }
```

### 5.4 Error Response Schema

Consistent error envelope for 4xx/5xx:

```python
class ErrorResponse(BaseModel):
    """Standard error response body."""
    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    detail: Optional[str] = Field(None, description="Additional context")


# Usage in routes:
# raise HTTPException(
#     status_code=404,
#     detail=ErrorResponse(
#         error="CVE_NOT_FOUND",
#         message=f"CVE {cve_id} not found in NVD",
#     ).model_dump()
# )
```

### 5.5 Input Validation

Query parameter validation in routes using Pydantic + FastAPI's `Query()`:

```python
from fastapi import Query
from pydantic import field_validator
import re


CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d{1,7}(\*)?$", re.IGNORECASE)
SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def validate_cve_query(id: str = Query(..., min_length=3, max_length=30)) -> str:
    """Validate and normalize CVE ID query parameter."""
    normalized = id.upper().strip()
    if not CVE_ID_PATTERN.match(normalized):
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="INVALID_CVE_ID",
                message=f"'{id}' is not a valid CVE ID. Expected format: CVE-YYYY-NNNNN",
            ).model_dump(),
        )
    return normalized


def validate_severity(
    severity: Optional[str] = Query(None)
) -> Optional[str]:
    """Normalize and validate severity filter."""
    if severity is None:
        return None
    normalized = severity.upper().strip()
    if normalized not in SEVERITY_VALUES:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="INVALID_SEVERITY",
                message=f"Severity must be one of: {', '.join(sorted(SEVERITY_VALUES))}",
            ).model_dump(),
        )
    return normalized
```

---

## 6. Architectural Decisions Summary

### 6.1 Service Layer Structure

Phase 2 introduces these new service modules under `backend/services/`:

```
backend/services/
  nvd_service.py       # NVDClient: async wrapper around nvdlib
  cache_service.py     # CVECacheService: Redis get/set/ttl
  cve_service.py       # Orchestration: cache-aside, SWR, fallback logic
```

And routes:
```
backend/routes/
  cve.py              # /cve/search and /cve/latest endpoints (currently stubs)
```

### 6.2 Dependency Injection Chain

```
FastAPI route
  └── Depends(get_db)           → AsyncSession
  └── Depends(get_redis)        → aioredis.Redis
  └── Depends(get_cache_service)→ CVECacheService(redis)
  └── Depends(get_nvd_client)   → NVDClient(api_key)
  └── BackgroundTasks           → FastAPI-injected
```

### 6.3 New Dependencies to Add

Add to `backend/requirements.txt`:

```
nvdlib==0.7.6
tenacity==8.3.0
rapidfuzz==3.9.0
aiobreaker==1.1.0   # Optional for Phase 2; required for production hardening
```

### 6.4 Key Design Decisions Locked In

| Decision | Rationale |
|----------|-----------|
| nvdlib wrapped in `asyncio.to_thread` | nvdlib is sync-only; prevents event loop blocking |
| `float` not `Decimal` for CVSS scores | Pydantic v2 serializes Decimal as string; float is correct for JSON |
| Cache individual CVEs only | Paginated list caching would complicate invalidation and waste memory |
| Severity filter as Python post-filter (not NVD param for v4.0) | nvdlib lacks `cvssV4Severity` param; consistent behavior across both versions |
| Redis TTL jitter (±1h around 24h) | Prevents simultaneous bulk expiry (thundering herd) after initial load |
| Fuzzy search bounded to local DB only | 250k+ NVD CVEs too large for live fuzzy scan; local cache is practical scope |
| 503 (not 500) when NVD is down with no cache | 503 signals "service temporarily unavailable" vs 500 "our bug" |
| Stale-while-revalidate via FastAPI BackgroundTasks | Zero external dependency; sufficient for Phase 2 scale |

### 6.5 Failure Mode Matrix

| Failure | User Impact | Mitigation |
|---------|-------------|------------|
| NVD 429 (rate limited) | None — cache hit returns HTTP 200 | Tenacity retry → cache fallback |
| NVD 429, no cache | HTTP 503 with clear message | Logged; user retries later |
| Redis down | Cache bypassed; NVD queried directly | try/except wraps all Redis ops |
| nvdlib attribute missing (CVE has no CVSS) | Field returns null | `getattr(obj, attr, None)` throughout |
| DB down | Cache-only mode; no persistence | Separate concern; Redis is primary for reads |
| CVE not in NVD | HTTP 404 | `results[0]` guard; None → 404 |

---

## Sources

- [nvdlib PyPI](https://pypi.org/project/nvdlib/)
- [nvdlib GitHub (vehemont/nvdlib)](https://github.com/vehemont/nvdlib)
- [NVDLib CVE Documentation](https://nvdlib.com/en/latest/v2/CVEv2.html)
- [NVDLib Classes Module](https://nvdlib.com/en/latest/_modules/nvdlib/classes.html)
- [NVD Vulnerability APIs](https://nvd.nist.gov/developers/vulnerabilities)
- [NVD CVSS v4.0 Official Support](https://nvd.nist.gov/general/news/cvss-v4-0-official-support)
- [Building High-Performance APIs with FastAPI and Redis](https://redis.io/tutorials/develop/python/fastapi/)
- [How to Implement Cache Invalidation in FastAPI](https://oneuptime.com/blog/post/2026-02-02-fastapi-cache-invalidation/view)
- [FastAPI + HTTP Caching with Stale-While-Revalidate](https://medium.com/@hadiyolworld007/fastapi-http-caching-with-stale-while-revalidate-instant-feels-correct-data-5811297867ea)
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz)
- [Tenacity Retry Library](https://tenacity.readthedocs.io/)
- [aiobreaker Circuit Breaker](https://github.com/arlyon/aiobreaker)
- [Redis Key Patterns: Namespace, Version, Data Type, Id](https://kirillshevch.medium.com/redis-key-patterns-namespace-version-data-type-id-138ca62ce0d8)
- [Pydantic v2 Serialization](https://docs.pydantic.dev/latest/concepts/serialization/)

---

*Research completed: 2026-02-23*
*Phase: 02-backend-api-nvd-integration*
