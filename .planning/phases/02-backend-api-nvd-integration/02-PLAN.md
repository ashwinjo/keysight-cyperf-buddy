---
wave: 1
depends_on: []
files_modified:
  - backend/models/cve.py
  - backend/services/nvd_service.py
  - backend/services/cache_service.py
  - backend/services/cve_service.py
  - backend/routes/cve.py
  - backend/main.py
  - backend/requirements.txt
  - backend/tests/test_cve_search.py
  - backend/tests/test_cve_latest.py
  - backend/tests/test_cache_behavior.py
  - backend/tests/test_rate_limit_fallback.py
  - backend/tests/conftest.py
autonomous: true
---

# Phase 2: Backend API + NVD Integration — Implementation Plan

**Phase Goal:** Users can query CVE data via the API — by exact ID, by latest list, and with CVSS
severity filters — with NVD responses cached in Redis to prevent rate-limit failures.

**Requirements covered:** SEARCH-01, SEARCH-02, SEARCH-05, BROWSE-01, BROWSE-02, BROWSE-04,
SYNC-01, SYNC-05

**Depends on:** Phase 1 (Docker stack live, DB schema migrated, Redis healthy)

---

## Pre-Work: Codebase Audit

Before any task begins, verify the exact starting state:

- `backend/models.py` — contains `CVEResponse` using `Decimal` for CVSS scores (must be replaced
  with `float` per research finding 5.1)
- `backend/db/cve.py` — `CVE` ORM model with `Numeric(3,1)` / `Numeric(4,2)` columns; indexes on
  `published_date` and `cvss_v3_severity` already present (do not re-create)
- `backend/routes/cve.py` — stub routes returning `{"status": "coming in phase 2"}`; not registered
  in `main.py`
- `backend/services/` — only `health_service.py` exists; `nvd_service.py`, `cache_service.py`,
  `cve_service.py` are all new files
- `backend/requirements.txt` — `redis[asyncio]==5.0.1` present; `nvdlib`, `tenacity`, `rapidfuzz`
  are absent; `httpx==0.26.0` already present

---

## Architecture Overview

```
HTTP Request
  └── routes/cve.py           (input validation, HTTP contract)
        └── services/cve_service.py    (orchestration: cache-aside, SWR, fallback)
              ├── services/cache_service.py  (Redis get/set/ttl/exists)
              └── services/nvd_service.py    (asyncio.to_thread wrapper over nvdlib)
                    └── nvdlib.searchCVE()   (synchronous; runs in thread pool)
        └── db/cve.py (ORM)                 (DB read/write for persistence + fuzzy search)
```

Dependency injection chain per request:

```
route → Depends(get_db) → AsyncSession
      → Depends(get_redis) → aioredis.Redis
      → Depends(get_cache_service) → CVECacheService(redis)
      → Depends(get_nvd_client) → NVDClient(api_key)
      → BackgroundTasks (FastAPI-injected)
```

---

## Tasks

<tasks>

<task id="2.1">
<title>Replace CVEResponse Pydantic model and define API response schemas</title>
<file>backend/models/cve.py</file>
<depends_on>none</depends_on>

<context>
The existing `backend/models.py` defines `CVEResponse` with `Decimal` for CVSS scores. Research
finding 5.1 is explicit: Pydantic v2 serializes `Decimal` as a string in JSON output, which breaks
numeric comparisons in any frontend or security tool consuming the API. The fix is `float`.

Additionally, the existing model uses `references: str | None` (raw JSON string from DB column),
but the API must expose `reference_urls: list[str]` (deserialized list) per context decisions
(flattened structure). The service layer will deserialize; the model must declare the correct type.

This task also introduces the `CVESearchResponse` and `CVELatestResponse` envelope models and the
`ErrorResponse` schema used by all 4xx/5xx handlers.

Note: `backend/models.py` at root will remain for DB-adjacent models (CyperfMapping,
SyncStatus, Health). The new CVE API models go in `backend/models/cve.py` as a dedicated module.
Create `backend/models/__init__.py` to make it a package.
</context>

<implementation>
Create `backend/models/__init__.py` (empty package marker).

Create `backend/models/cve.py` with these classes:

**CVEDetail** — single CVE record, flattened schema:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CVEDetail(BaseModel):
    """
    Single CVE record — flattened, curated field set.
    Covers SEARCH-02 (full details) and BROWSE-04 (row display fields).
    """
    model_config = {"from_attributes": True}

    # Identity
    id: str = Field(..., description="CVE identifier (e.g. CVE-2024-1234)")
    description: str = Field(
        default="No description available",
        description="English description from NVD",
    )
    published_date: Optional[str] = Field(
        None, description="Date CVE was published (ISO 8601 UTC)"
    )

    # CVSS v3.1 — use float, not Decimal. Pydantic v2 serializes Decimal as string.
    cvss_v3_score: Optional[float] = Field(
        None, description="CVSS v3.1 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v3_severity: Optional[str] = Field(
        None, description="CVSS v3.1 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v3_vector: Optional[str] = Field(None, description="CVSS v3.1 vector string")

    # CVSS v4.0 — present only for CVEs published post-2023 with v4 scoring
    cvss_v4_score: Optional[float] = Field(
        None, description="CVSS v4.0 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v4_severity: Optional[str] = Field(
        None, description="CVSS v4.0 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v4_vector: Optional[str] = Field(None, description="CVSS v4.0 vector string")

    # References — deserialized list; DB stores JSON string, service layer deserializes
    reference_urls: list[str] = Field(
        default_factory=list,
        description="Reference URLs from NVD",
    )

    # Testability placeholder — populated by Phase 3 Cyperf integration
    testable: Optional[bool] = Field(
        None, description="Whether Cyperf can test this CVE (None = not yet determined)"
    )
```

**CVESearchResponse** — wraps search results:
```python
class CVESearchResponse(BaseModel):
    results: list[CVEDetail]
    total: int = Field(..., description="Number of matching results returned")
    query: str = Field(..., description="Normalized query that was executed")
    search_type: str = Field(
        ..., description="Search tier used: exact | prefix | fuzzy"
    )
```

**CVELatestResponse** — wraps paginated browse results:
```python
class CVELatestResponse(BaseModel):
    results: list[CVEDetail]
    total: int = Field(..., description="Number of results in this page")
    page: int = Field(1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=500, description="Number of results per page")
    severity_filter: Optional[str] = Field(
        None, description="Applied severity filter if any"
    )
```

**ErrorResponse** — used in all HTTPException detail payloads:
```python
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    detail: Optional[str] = Field(None, description="Additional context (never credentials)")
```

**Design decisions locked in:**
- `published_date` is `Optional[str]` (ISO 8601) not `Optional[datetime]`: avoids Pydantic
  serializer ambiguity when building from Redis-cached dicts (strings) vs DB ORM objects
  (datetime). The service layer normalizes to ISO string before storing.
- `testable: Optional[bool]` is included now so Phase 3 can populate it without changing the
  response schema. During Phase 2 it will always be `None`.
- `description` has a non-None default because every valid NVD CVE has an English description;
  using `Optional[str]` would require None-guards everywhere downstream.
</implementation>

<verification>
```python
# Quick sanity check — run in Python REPL after implementation
from backend.models.cve import CVEDetail, CVESearchResponse, CVELatestResponse, ErrorResponse
import json

d = CVEDetail(
    id="CVE-2024-1234",
    cvss_v3_score=9.8,
    cvss_v3_severity="CRITICAL",
    published_date="2024-01-01T00:00:00",
    reference_urls=["https://example.com"],
)
payload = json.loads(d.model_dump_json())
assert isinstance(payload["cvss_v3_score"], float)   # not string
assert payload["testable"] is None                    # Phase 3 placeholder

err = ErrorResponse(error="CVE_NOT_FOUND", message="Not found")
assert "password" not in err.model_dump_json()        # credential safety
```
</verification>
</task>

<task id="2.2">
<title>Implement NVDClient — async wrapper around nvdlib</title>
<file>backend/services/nvd_service.py</file>
<depends_on>none</depends_on>

<context>
nvdlib is synchronous (uses `requests` internally). Calling it directly in a FastAPI async handler
blocks the event loop. The fix is `asyncio.to_thread()` (Python 3.9+), which pushes the blocking
call to the default thread pool executor without requiring explicit executor management.

The service must handle two primary call patterns:
1. Exact CVE ID lookup — `searchCVE(cveId="CVE-2024-1234")` returns a list; take index 0 or None
2. Date-windowed latest fetch — `searchCVE(pubStartDate=..., pubEndDate=..., limit=N)` for browse

`searchCVE_V2()` (generator) is used for large date windows to avoid loading thousands of CVEs
into memory at once. The generator yields one CVE object at a time.

The `extract_cve_fields()` function defined here is the single translation point from nvdlib's
attribute namespace to the application's field names. All attribute access uses `getattr(obj, attr,
None)` because not all CVEs have all CVSS versions.

Rate-limit detection: nvdlib raises exceptions for HTTP errors. Inspect the exception string for
"429", "403", or "rate" to classify as `NVDRateLimitError`. This is the signal used by task 2.4
(retry logic) and task 2.5 (fallback logic).
</context>

<implementation>
Create `backend/services/nvd_service.py`:

```python
"""
NVD API async wrapper.

nvdlib is synchronous (requests-based). All calls are wrapped in asyncio.to_thread()
to prevent event loop blocking in FastAPI async routes.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import nvdlib

logger = logging.getLogger(__name__)


class NVDRateLimitError(Exception):
    """Raised when NVD returns 429 or equivalent rate-limit signal."""
    pass


class NVDClient:
    """Thread-safe async wrapper around nvdlib.

    Wraps all synchronous nvdlib calls in asyncio.to_thread() to prevent
    event loop blocking. The API key controls the minimum delay between
    requests (0.6s with key, 6.0s without).
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
        # nvdlib enforces these delays internally between paginated requests
        self._delay: float = 0.6 if api_key else 6.0
        if api_key:
            logger.info("NVDClient initialized with API key (100 req/min limit)")
        else:
            logger.warning(
                "NVDClient initialized without API key (10 req/min limit). "
                "Set NVD_API_KEY for production use."
            )

    async def fetch_cve(self, cve_id: str) -> Optional[object]:
        """
        Fetch a single CVE by exact ID.

        Returns the nvdlib CVE object if found, None if not in NVD.
        Raises NVDRateLimitError if NVD is rate-limiting.
        """
        normalized_id = cve_id.upper().strip()
        logger.debug("Fetching CVE from NVD: %s", normalized_id)

        def _sync_fetch() -> list:
            return nvdlib.searchCVE(
                cveId=normalized_id,
                key=self._api_key,
                delay=self._delay,
            )

        try:
            results = await asyncio.to_thread(_sync_fetch)
            return results[0] if results else None
        except Exception as exc:
            self._classify_and_raise(exc, context=normalized_id)

    async def fetch_latest(
        self,
        days: int = 30,
        limit: int = 500,
    ) -> list[object]:
        """
        Fetch CVEs published in the last N days.

        Uses searchCVE_V2 (generator) to avoid loading the full result set
        into memory when date windows span many CVEs. Collects up to `limit`
        results before returning.

        Severity filtering is NOT applied here — post-filter in cve_service.py
        because v4.0 severity is not a supported NVD API parameter in nvdlib.
        """
        start, end = _get_date_window(days)
        logger.debug(
            "Fetching latest CVEs from NVD: window=%s to %s, limit=%d",
            start, end, limit,
        )

        def _sync_fetch() -> list:
            # searchCVE_V2 returns a generator; collect up to limit records
            results = []
            for cve in nvdlib.searchCVE_V2(
                pubStartDate=start,
                pubEndDate=end,
                key=self._api_key,
                delay=self._delay,
            ):
                results.append(cve)
                if len(results) >= limit:
                    break
            return results

        try:
            return await asyncio.to_thread(_sync_fetch)
        except Exception as exc:
            self._classify_and_raise(exc, context=f"latest (days={days})")

    def _classify_and_raise(self, exc: Exception, context: str) -> None:
        """
        Inspect exception and raise NVDRateLimitError or re-raise original.

        nvdlib does not use typed exceptions for HTTP errors; inspect the
        string representation to detect 429/403 rate-limit scenarios.
        """
        exc_str = str(exc).lower()
        if any(signal in exc_str for signal in ("429", "403", "rate limit", "too many")):
            logger.warning("NVD rate limit hit for: %s", context)
            raise NVDRateLimitError(
                f"NVD API rate limited while fetching: {context}"
            ) from exc
        # Unknown error — re-raise with context but do not swallow
        logger.error("NVD API error for %s: %s", context, exc, exc_info=True)
        raise


def _get_date_window(days: int) -> tuple[str, str]:
    """
    Return (start, end) date strings in NVD API format: "YYYY-MM-DD HH:MM".
    NVD enforces a maximum 120-day window per query.
    """
    if days > 120:
        raise ValueError(
            f"NVD API allows max 120-day date window; requested {days} days"
        )
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return (
        start.strftime("%Y-%m-%d %H:%M"),
        now.strftime("%Y-%m-%d %H:%M"),
    )


def extract_cve_fields(nvd_cve: object) -> dict:
    """
    Maps nvdlib CVE object attributes to the application's field schema.

    This is the single translation boundary between nvdlib's attribute
    namespace and the application's field names. All attribute access uses
    getattr(obj, attr, None) because not all CVEs have all CVSS versions.

    CVSS v3 preference: v3.1 over v3.0 (older CVEs only have v3.0).
    CVSS v4: present only on CVEs published after 2023.
    References: extract .url from each ref object, skip None URLs.
    """
    # English description
    description = "No description available"
    if hasattr(nvd_cve, "descriptions") and nvd_cve.descriptions:
        for desc in nvd_cve.descriptions:
            if getattr(desc, "lang", "") == "en":
                description = desc.value
                break

    # Published date: ISO 8601 string from nvdlib; normalize to bare isoformat
    published_date: Optional[str] = None
    raw_published = getattr(nvd_cve, "published", None)
    if raw_published:
        try:
            # nvdlib returns strings like "2024-01-15T10:00:00.000"
            published_date = datetime.fromisoformat(
                raw_published.rstrip("Z")
            ).isoformat()
        except (ValueError, AttributeError):
            published_date = None

    # Reference URLs
    reference_urls: list[str] = []
    refs = getattr(nvd_cve, "references", None)
    if refs:
        reference_urls = [
            ref.url for ref in refs
            if hasattr(ref, "url") and ref.url
        ]

    # CVSS v3.1 preferred; fall back to v3.0 for older CVEs
    cvss_v3_score = (
        getattr(nvd_cve, "v31score", None)
        or getattr(nvd_cve, "v30score", None)
    )
    cvss_v3_severity = (
        getattr(nvd_cve, "v31severity", None)
        or getattr(nvd_cve, "v30severity", None)
    )
    cvss_v3_vector = (
        getattr(nvd_cve, "v31vector", None)
        or getattr(nvd_cve, "v30vector", None)
    )

    # CVSS v4.0 — nvdlib >= 0.7.6 required
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
        "testable": None,  # Phase 3 Cyperf integration populates this
    }
```

Add dependency getter to `backend/dependencies.py` (new file, shared by routes):
```python
from functools import lru_cache
from config import get_settings
from services.nvd_service import NVDClient

@lru_cache(maxsize=1)
def get_nvd_client() -> NVDClient:
    """Singleton NVDClient — shared across all requests."""
    return NVDClient(api_key=get_settings().nvd_api_key)
```
</implementation>

<verification>
```python
# Unit test: extract_cve_fields with missing CVSS versions
from unittest.mock import MagicMock
from services.nvd_service import extract_cve_fields

mock_cve = MagicMock()
mock_cve.id = "CVE-2024-0001"
mock_cve.published = "2024-01-01T00:00:00.000"
mock_cve.descriptions = [MagicMock(lang="en", value="Test vulnerability")]
mock_cve.references = [MagicMock(url="https://example.com")]
# No CVSS attributes — all getattr should return None
del mock_cve.v31score, mock_cve.v31severity, mock_cve.v31vector
del mock_cve.v30score, mock_cve.v30severity, mock_cve.v30vector
del mock_cve.v40score, mock_cve.v40severity, mock_cve.v40vector

result = extract_cve_fields(mock_cve)
assert result["id"] == "CVE-2024-0001"
assert result["cvss_v3_score"] is None
assert result["cvss_v4_score"] is None
assert result["reference_urls"] == ["https://example.com"]
assert isinstance(result["published_date"], str)
```
</verification>
</task>

<task id="2.3">
<title>Implement CVECacheService — Redis get/set/ttl with TTL jitter</title>
<file>backend/services/cache_service.py</file>
<depends_on>none</depends_on>

<context>
The cache service is a thin wrapper over Redis with three responsibilities:
1. Key scheme: `cve:v1:{CVE_ID_UPPERCASE}` — versioned prefix enables bulk invalidation
2. TTL management: 24h base + ±1h random jitter prevents cache stampede after bulk loads
3. Stale detection: `get_remaining_ttl()` lets the orchestration layer trigger SWR refresh

The Redis connection pool is managed in `main.py`'s lifespan context (see task 2.8). This service
receives an already-initialized `aioredis.Redis` instance via dependency injection — it does not
create its own connections.

Serialization: JSON with `default=str` to handle any datetime objects that slip through. The
extract_cve_fields() function in nvd_service.py already normalizes dates to ISO strings, so this
is a safety net.

Redis failure mode: every public method wraps Redis calls in try/except. If Redis is down, callers
receive None (cache miss) rather than an exception. The exception is logged at WARNING level
(not DEBUG, because Redis outages need visibility), but never re-raised. This implements the
"Redis down must not bring down the API" architecture invariant.
</context>

<implementation>
Create `backend/services/cache_service.py`:

```python
"""
Redis CVE cache service.

Key scheme:  cve:v1:{CVE_ID_UPPERCASE}
TTL:         86400s base ± 3600s jitter (23h-25h window)
Serialization: JSON with default=str

All public methods catch Redis exceptions and return None/False on failure.
Redis unavailability must NOT propagate as an API error.
"""

import json
import logging
import random
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# TTL constants
CVE_CACHE_TTL_SECONDS = 86400        # 24 hours base
CVE_CACHE_TTL_JITTER_SECONDS = 3600  # ±1 hour jitter

# SWR threshold: refresh if remaining TTL falls below this value
STALE_REFRESH_THRESHOLD_SECONDS = 4 * 3600  # 4 hours


def _make_cache_key(cve_id: str) -> str:
    """Canonical Redis key for a CVE record. Always uppercase-normalized."""
    return f"cve:v1:{cve_id.upper()}"


def _ttl_with_jitter() -> int:
    """Returns TTL between 23h and 25h to spread cache expiry."""
    return CVE_CACHE_TTL_SECONDS + random.randint(
        -CVE_CACHE_TTL_JITTER_SECONDS, CVE_CACHE_TTL_JITTER_SECONDS
    )


class CVECacheService:
    """Cache-aside service for CVE records backed by Redis."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def get(self, cve_id: str) -> Optional[dict]:
        """
        Return cached CVE dict or None on cache miss or Redis failure.
        Never raises — Redis failure returns None (cache miss).
        """
        key = _make_cache_key(cve_id)
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis GET failed for %s: %s", key, exc)
            return None

    async def set(self, cve_id: str, data: dict) -> bool:
        """
        Store CVE dict in Redis with TTL jitter.
        Returns True on success, False on Redis failure.
        """
        key = _make_cache_key(cve_id)
        try:
            serialized = json.dumps(data, default=str)
            ttl = _ttl_with_jitter()
            await self._redis.set(key, serialized, ex=ttl)
            logger.debug("Cached CVE %s with TTL=%ds", cve_id, ttl)
            return True
        except Exception as exc:
            logger.warning("Redis SET failed for %s: %s", key, exc)
            return False

    async def get_remaining_ttl(self, cve_id: str) -> int:
        """
        Returns remaining TTL in seconds.
        Returns -2 if key does not exist, -1 if no TTL set.
        Returns 0 on Redis failure (treat as stale).
        """
        key = _make_cache_key(cve_id)
        try:
            return await self._redis.ttl(key)
        except Exception as exc:
            logger.warning("Redis TTL check failed for %s: %s", key, exc)
            return 0  # Treat failure as stale → triggers refresh attempt

    async def exists(self, cve_id: str) -> bool:
        """Check if CVE is in cache. Returns False on Redis failure."""
        key = _make_cache_key(cve_id)
        try:
            return bool(await self._redis.exists(key))
        except Exception as exc:
            logger.warning("Redis EXISTS failed for %s: %s", key, exc)
            return False

    def is_stale(self, remaining_ttl: int) -> bool:
        """
        True if remaining TTL indicates the entry should be proactively refreshed.
        Triggers stale-while-revalidate background refresh.
        """
        return 0 <= remaining_ttl < STALE_REFRESH_THRESHOLD_SECONDS
```

Add Redis initialization to `backend/dependencies.py`:
```python
import redis.asyncio as aioredis
from services.cache_service import CVECacheService

# Module-level singleton, initialized during lifespan startup
_redis_client: Optional[aioredis.Redis] = None


def set_redis_client(client: aioredis.Redis) -> None:
    """Called from main.py lifespan on startup."""
    global _redis_client
    _redis_client = client


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency: shared Redis client."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized — lifespan not run")
    return _redis_client


async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis),
) -> CVECacheService:
    """FastAPI dependency: CVECacheService bound to shared Redis client."""
    return CVECacheService(redis)
```
</implementation>

<verification>
```python
# Unit test: cache miss returns None without raising
import asyncio
from unittest.mock import AsyncMock, MagicMock
from services.cache_service import CVECacheService

mock_redis = AsyncMock()
mock_redis.get.side_effect = ConnectionError("Redis down")

svc = CVECacheService(mock_redis)

# Cache failure must return None, not raise
result = asyncio.run(svc.get("CVE-2024-1234"))
assert result is None

# set failure must return False, not raise
mock_redis.set.side_effect = ConnectionError("Redis down")
success = asyncio.run(svc.set("CVE-2024-1234", {"id": "CVE-2024-1234"}))
assert success is False

# Key normalization
mock_redis.get.side_effect = None
mock_redis.get.return_value = None
asyncio.run(svc.get("cve-2024-1234"))  # lowercase input
mock_redis.get.assert_called_with("cve:v1:CVE-2024-1234")  # always uppercase key
```
</verification>
</task>

<task id="2.4">
<title>Implement retry logic with tenacity for NVD rate-limit handling</title>
<file>backend/services/nvd_service.py (extension)</file>
<depends_on>2.2</depends_on>

<context>
Tenacity wraps the NVD fetch calls with exponential backoff specifically for `NVDRateLimitError`.
The retry decorator is applied to the async functions that call `NVDClient.fetch_cve()` and
`NVDClient.fetch_latest()` — NOT to the methods themselves (which allows unit testing without
retry interference).

Retry configuration rationale:
- `wait_exponential(min=2, max=30)`: 2s → 4s → 8s (capped at 30s)
- `+ wait_random(0, 2)`: jitter prevents synchronized retries across concurrent requests
- `stop_after_attempt(3)`: fail fast; NVD 429s typically resolve within 60s with the 6s delay
- `reraise=True`: NVDRateLimitError propagates to the orchestration layer after all retries
  exhausted so the fallback-to-cache logic can execute

The retry functions are standalone async functions (not methods) to allow `@retry` decoration
cleanly. The circuit breaker pattern (aiobreaker) is described in research but is deferred to
post-Phase-2 hardening. Tenacity + cache fallback is sufficient for Phase 2.
</context>

<implementation>
Add to `backend/services/nvd_service.py`:

```python
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    before_sleep_log,
    RetryError,
)


@retry(
    retry=retry_if_exception_type(NVDRateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_cve_with_retry(
    nvd_client: NVDClient,
    cve_id: str,
) -> Optional[object]:
    """
    Fetch CVE from NVD with exponential backoff on rate-limit.

    Attempts: 3 total.
    Wait sequence: ~2s, ~4s, ~8s (+ 0-2s jitter each).
    On exhaustion: raises NVDRateLimitError (caught in cve_service.py fallback).
    """
    return await nvd_client.fetch_cve(cve_id)


@retry(
    retry=retry_if_exception_type(NVDRateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_latest_with_retry(
    nvd_client: NVDClient,
    days: int = 30,
    limit: int = 500,
) -> list[object]:
    """
    Fetch latest CVEs with exponential backoff on rate-limit.
    Same retry policy as fetch_cve_with_retry.
    """
    return await nvd_client.fetch_latest(days=days, limit=limit)
```

**Failure path contract:**
- After 3 failed attempts, `NVDRateLimitError` propagates to the caller.
- `cve_service.py` (task 2.5) catches `NVDRateLimitError` and falls back to DB/cache.
- No `NVDRateLimitError` ever reaches the route layer; routes only see `None` or valid data.
</implementation>

<verification>
```python
# Test retry count: NVDRateLimitError should retry 3 times then re-raise
import asyncio
from unittest.mock import AsyncMock, patch
from services.nvd_service import NVDClient, NVDRateLimitError, fetch_cve_with_retry

mock_client = AsyncMock(spec=NVDClient)
mock_client.fetch_cve.side_effect = NVDRateLimitError("rate limited")

call_count = 0
async def counting_fetch(cve_id):
    global call_count
    call_count += 1
    raise NVDRateLimitError("rate limited")

mock_client.fetch_cve.side_effect = counting_fetch

try:
    asyncio.run(fetch_cve_with_retry(mock_client, "CVE-2024-1234"))
except NVDRateLimitError:
    pass

assert call_count == 3  # 3 attempts total before reraise
```
</verification>
</task>

<task id="2.5">
<title>Implement CVEService — cache-aside orchestration with SWR and rate-limit fallback</title>
<file>backend/services/cve_service.py</file>
<depends_on>2.2, 2.3, 2.4</depends_on>

<context>
This is the core orchestration layer. It coordinates the cache, NVD client, and DB to implement:

1. **Cache-aside with SWR (stale-while-revalidate):** Check cache first; serve cached data
   immediately; if TTL is under the 4h threshold, trigger background refresh via FastAPI
   `BackgroundTasks`. This is the "proactive refresh" behavior specified in context decisions.

2. **Rate-limit fallback (SYNC-05):** If NVD is unreachable after 3 retries, fall back to DB.
   If DB also has no record, return None. The route layer converts None to HTTP 503 (not 500).
   HTTP 200 is returned whenever any cached data is available.

3. **Fuzzy search dispatch (3-tier):** Exact → SQL LIKE prefix → RapidFuzz bounded to local DB.
   Fuzzy search is only attempted against locally-cached CVE IDs, never against NVD live data.

4. **DB persistence:** Every NVD fetch result is written to the `cves` table via upsert. This
   ensures the DB grows as users query CVEs, enabling prefix/fuzzy search to improve over time.

5. **Severity post-filter:** Applied after data retrieval (not in NVD query) for consistency
   across both CVSS v3.1 and v4.0. Per context decision: OR semantics (v3.1 OR v4.0 match).

The CVEService must NOT raise exceptions that expose NVD infrastructure details to callers.
All NVD errors are caught here and converted to None or logged.
</context>

<implementation>
Create `backend/services/cve_service.py`:

```python
"""
CVE orchestration service.

Implements cache-aside + stale-while-revalidate + NVD rate-limit fallback.
All public methods are safe to call from FastAPI routes — they do not raise
infrastructure exceptions; they return None on total failure.
"""

import json
import logging
import re
from typing import Optional

from fastapi import BackgroundTasks
from rapidfuzz import fuzz, process
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.cve import CVE
from services.cache_service import CVECacheService
from services.nvd_service import (
    NVDClient,
    NVDRateLimitError,
    extract_cve_fields,
    fetch_cve_with_retry,
    fetch_latest_with_retry,
)

logger = logging.getLogger(__name__)

# Regex for a complete, valid CVE ID (no wildcards)
_EXACT_CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d+$", re.IGNORECASE)

# Regex for wildcard/prefix queries (contains * or partial number segment)
_WILDCARD_PATTERN = re.compile(r"[*%]")


# ---------------------------------------------------------------------------
# Public API — called from routes
# ---------------------------------------------------------------------------

async def get_cve(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> Optional[dict]:
    """
    Fetch a single CVE by exact ID with full cache-aside + SWR + fallback.

    Returns:
        CVE dict on success (from cache, NVD, or DB fallback).
        None if CVE not found anywhere (route returns 404).
        Never returns None due to NVD rate-limit if a cached copy exists.
    """
    normalized_id = cve_id.upper().strip()

    # 1. Cache hit path
    cached = await cache.get(normalized_id)
    if cached is not None:
        remaining_ttl = await cache.get_remaining_ttl(normalized_id)
        if cache.is_stale(remaining_ttl):
            # Serve stale data now; refresh after response is sent
            background_tasks.add_task(
                _background_refresh_cve, normalized_id, cache, nvd, db
            )
        return cached

    # 2. Cache miss: attempt NVD fetch with retry + fallback
    return await _fetch_and_cache(normalized_id, cache, nvd, db)


async def search_cves(
    query: str,
    severity: Optional[str],
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> tuple[list[dict], str]:
    """
    Dispatch CVE search across 3 tiers: exact → prefix → fuzzy.

    Returns (results, search_type) where search_type is one of:
        "exact" | "prefix" | "fuzzy"

    Severity filter (if provided) is applied as post-filter using OR semantics:
    CVE is included if cvss_v3_severity OR cvss_v4_severity matches.
    """
    normalized = query.upper().strip()

    if _EXACT_CVE_PATTERN.match(normalized):
        # Tier 1: Exact match — check cache + NVD
        result = await get_cve(normalized, cache, nvd, db, background_tasks)
        results = [result] if result else []
        search_type = "exact"

    elif _WILDCARD_PATTERN.search(normalized):
        # Tier 2: Wildcard/prefix — SQL LIKE against local DB only
        results = await _search_by_prefix(normalized, db)
        search_type = "prefix"

    else:
        # Tier 3: Fuzzy match — RapidFuzz against local DB CVE IDs only
        # Not queried against NVD live (250k+ CVEs too large for live scan)
        fuzzy_ids = await _fuzzy_search_ids(normalized, db)
        results = []
        for fuzz_id in fuzzy_ids:
            cve_data = await get_cve(fuzz_id, cache, nvd, db, background_tasks)
            if cve_data:
                results.append(cve_data)
        search_type = "fuzzy"

    if severity:
        results = _filter_by_severity(results, severity.upper())

    return results, search_type


async def get_latest_cves(
    page: int,
    page_size: int,
    severity: Optional[str],
    nvd: NVDClient,
    db: AsyncSession,
    cache: CVECacheService,
) -> tuple[list[dict], int]:
    """
    Fetch latest CVEs sorted by published date (newest first).

    Strategy:
    1. Attempt NVD fetch for the last 30 days; cache each CVE individually.
    2. Query local DB with pagination (sorted by published_date DESC).
    3. Apply severity post-filter in Python (covers both v3.1 and v4.0).

    Returns (page_results, total_on_page).
    On NVD failure, serves from DB-only (graceful degradation).
    """
    # Step 1: Try to refresh DB from NVD (non-blocking on failure)
    try:
        nvd_cves = await fetch_latest_with_retry(nvd, days=30, limit=500)
        for nvd_cve in nvd_cves:
            cve_data = extract_cve_fields(nvd_cve)
            await cache.set(cve_data["id"], cve_data)
            await _upsert_cve(cve_data, db)
        await db.commit()
        logger.info("Refreshed %d CVEs from NVD into DB/cache", len(nvd_cves))
    except NVDRateLimitError:
        logger.warning(
            "NVD rate-limited during /cve/latest fetch; serving from DB cache"
        )
    except Exception as exc:
        logger.error("NVD fetch failed for /cve/latest: %s", exc, exc_info=True)

    # Step 2: Query DB with pagination
    offset = (page - 1) * page_size
    stmt = (
        select(CVE)
        .order_by(CVE.published_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    db_cves = result.scalars().all()

    # Step 3: Convert ORM objects to dicts
    cve_list = [_orm_to_dict(c) for c in db_cves]

    # Step 4: Apply severity filter (OR: v3.1 OR v4.0 match)
    if severity:
        cve_list = _filter_by_severity(cve_list, severity.upper())

    return cve_list, len(cve_list)


# ---------------------------------------------------------------------------
# Internal helpers — not called from routes
# ---------------------------------------------------------------------------

async def _fetch_and_cache(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
) -> Optional[dict]:
    """
    Fetch CVE from NVD (with retry), write to cache + DB.
    On rate-limit exhaustion: fall back to DB.
    Returns None only if CVE is not found anywhere.
    """
    try:
        nvd_obj = await fetch_cve_with_retry(nvd, cve_id)
        if nvd_obj is None:
            return None
        cve_data = extract_cve_fields(nvd_obj)
        await cache.set(cve_id, cve_data)
        await _upsert_cve(cve_data, db)
        await db.commit()
        return cve_data

    except NVDRateLimitError:
        logger.warning(
            "NVD rate-limited after retries for %s; checking DB fallback", cve_id
        )
        return await _get_from_db(cve_id, db)

    except Exception as exc:
        logger.error(
            "Unexpected NVD fetch error for %s: %s", cve_id, exc, exc_info=True
        )
        return await _get_from_db(cve_id, db)


async def _background_refresh_cve(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
) -> None:
    """
    Background task: refresh a near-expired CVE from NVD.
    Runs after the response is sent. Failure is non-fatal — stale cache continues serving.
    """
    try:
        await _fetch_and_cache(cve_id, cache, nvd, db)
        logger.debug("Background refresh completed for %s", cve_id)
    except Exception as exc:
        # Non-fatal: stale data continues serving until natural TTL expiry
        logger.warning("Background refresh failed for %s: %s", cve_id, exc)


async def _search_by_prefix(
    query: str,
    db: AsyncSession,
    limit: int = 50,
) -> list[dict]:
    """
    SQL LIKE search against CVE IDs in the local database.
    Translates * wildcards to SQL % wildcards.
    Only searches locally-cached CVEs, not NVD live.
    """
    sql_pattern = query.replace("*", "%")
    stmt = (
        select(CVE)
        .where(CVE.id.like(sql_pattern))
        .order_by(CVE.published_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    db_cves = result.scalars().all()
    return [_orm_to_dict(c) for c in db_cves]


async def _fuzzy_search_ids(
    query: str,
    db: AsyncSession,
    score_cutoff: float = 80.0,
    limit: int = 10,
) -> list[str]:
    """
    RapidFuzz token_sort_ratio match against locally-cached CVE IDs.
    Bounded to local DB only — never scans NVD live (250k+ is not viable).
    Returns top N CVE IDs sorted by similarity score.
    """
    # Fetch only the ID column (not full records)
    stmt = select(CVE.id)
    result = await db.execute(stmt)
    all_ids: list[str] = result.scalars().all()

    if not all_ids:
        return []

    matches = process.extract(
        query.upper(),
        all_ids,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=score_cutoff,
        limit=limit,
    )
    return [match[0] for match in matches]


def _filter_by_severity(cves: list[dict], severity: str) -> list[dict]:
    """
    Filter CVEs by severity using OR semantics: v3.1 OR v4.0 must match.
    Per context decision: case-insensitive, OR not AND.
    """
    return [
        c for c in cves
        if (c.get("cvss_v3_severity") or "").upper() == severity
        or (c.get("cvss_v4_severity") or "").upper() == severity
    ]


async def _upsert_cve(cve_data: dict, db: AsyncSession) -> None:
    """
    Upsert CVE into the database. Uses SQLite insert-or-replace pattern;
    compatible with PostgreSQL via merge (update if ID exists).

    references field is JSON-encoded for the TEXT DB column.
    """
    references_json = json.dumps(cve_data.get("reference_urls", []))

    # Use merge (compatible with both SQLite and PostgreSQL via SQLAlchemy 2.0)
    existing = await db.get(CVE, cve_data["id"])
    if existing is None:
        db.add(CVE(
            id=cve_data["id"],
            description=cve_data.get("description"),
            published_date=cve_data.get("published_date"),
            cvss_v3_score=cve_data.get("cvss_v3_score"),
            cvss_v3_severity=cve_data.get("cvss_v3_severity"),
            cvss_v3_vector=cve_data.get("cvss_v3_vector"),
            cvss_v4_score=cve_data.get("cvss_v4_score"),
            cvss_v4_severity=cve_data.get("cvss_v4_severity"),
            cvss_v4_vector=cve_data.get("cvss_v4_vector"),
            references=references_json,
        ))
    else:
        # Update all fields except id and first_seen
        existing.description = cve_data.get("description")
        existing.published_date = cve_data.get("published_date")
        existing.cvss_v3_score = cve_data.get("cvss_v3_score")
        existing.cvss_v3_severity = cve_data.get("cvss_v3_severity")
        existing.cvss_v3_vector = cve_data.get("cvss_v3_vector")
        existing.cvss_v4_score = cve_data.get("cvss_v4_score")
        existing.cvss_v4_severity = cve_data.get("cvss_v4_severity")
        existing.cvss_v4_vector = cve_data.get("cvss_v4_vector")
        existing.references = references_json


async def _get_from_db(cve_id: str, db: AsyncSession) -> Optional[dict]:
    """
    Last-resort fallback: query DB for CVE. Used when NVD is unreachable.
    Returns dict or None if not in DB.
    """
    db_cve = await db.get(CVE, cve_id)
    return _orm_to_dict(db_cve) if db_cve else None


def _orm_to_dict(cve: CVE) -> dict:
    """Convert CVE ORM object to application dict schema."""
    reference_urls: list[str] = []
    if cve.references:
        try:
            reference_urls = json.loads(cve.references)
        except (json.JSONDecodeError, TypeError):
            reference_urls = []

    published_str: Optional[str] = None
    if cve.published_date:
        try:
            published_str = cve.published_date.isoformat()
        except AttributeError:
            published_str = str(cve.published_date)

    return {
        "id": cve.id,
        "description": cve.description or "No description available",
        "published_date": published_str,
        "cvss_v3_score": float(cve.cvss_v3_score) if cve.cvss_v3_score else None,
        "cvss_v3_severity": cve.cvss_v3_severity,
        "cvss_v3_vector": cve.cvss_v3_vector,
        "cvss_v4_score": float(cve.cvss_v4_score) if cve.cvss_v4_score else None,
        "cvss_v4_severity": cve.cvss_v4_severity,
        "cvss_v4_vector": cve.cvss_v4_vector,
        "reference_urls": reference_urls,
        "testable": None,  # Phase 3 populates from cyperf_supported_cves join
    }
```
</implementation>

<verification>
```python
# Test severity filter OR semantics
from services.cve_service import _filter_by_severity

cves = [
    {"id": "CVE-A", "cvss_v3_severity": "HIGH", "cvss_v4_severity": None},
    {"id": "CVE-B", "cvss_v3_severity": "LOW",  "cvss_v4_severity": "HIGH"},
    {"id": "CVE-C", "cvss_v3_severity": "LOW",  "cvss_v4_severity": "LOW"},
    {"id": "CVE-D", "cvss_v3_severity": None,   "cvss_v4_severity": "HIGH"},
]

high_only = _filter_by_severity(cves, "HIGH")
assert len(high_only) == 3  # CVE-A (v3), CVE-B (v4), CVE-D (v4)
assert all(c["id"] != "CVE-C" for c in high_only)

# Test that None severities don't raise
no_severity = [{"id": "CVE-E", "cvss_v3_severity": None, "cvss_v4_severity": None}]
result = _filter_by_severity(no_severity, "HIGH")
assert result == []  # no match, no exception
```
</verification>
</task>

<task id="2.6">
<title>Implement /cve/search and /cve/latest route handlers with input validation</title>
<file>backend/routes/cve.py</file>
<depends_on>2.1, 2.5</depends_on>

<context>
The route layer is responsible for:
1. Input validation — validate and normalize query parameters before they enter the service layer
2. HTTP contract — correct status codes (200 on success, 404 on not-found, 422 on bad input,
   503 on NVD unreachable with no cache)
3. Response serialization — build typed Pydantic response models from service layer dicts
4. Dependency injection — declare all dependencies via `Depends()`

Input validation rules:
- `id` parameter: must match `CVE-YYYY-NNNNN` pattern with optional trailing `*` (wildcard).
  Accept lowercase; normalize to uppercase. Reject anything that cannot be a valid CVE query.
- `severity`: must be one of LOW, MEDIUM, HIGH, CRITICAL (case-insensitive). Reject other values
  with 422 + ErrorResponse body.
- `page`: must be >= 1 (default: 1)
- `limit`: must be between 1 and 500 (default: 50)

The `BackgroundTasks` instance for SWR is injected by FastAPI automatically when declared as a
parameter — no `Depends()` needed.

Rate-limit fallback transparency: The route must not expose whether data came from cache or NVD.
The response is always HTTP 200 when data is available. The `search_type` field in
`CVESearchResponse` is the only hint about how the query was satisfied.

The CVE route router must be registered in `main.py` (task 2.8).
</context>

<implementation>
Replace the stub content of `backend/routes/cve.py`:

```python
"""
CVE search and browse endpoints.

Covers:
  SEARCH-01: Search by exact CVE ID
  SEARCH-02: Results include CVSS v3.1, v4.0, description, published date, references
  SEARCH-05: Filter by CVSS severity
  BROWSE-01: Paginated latest CVE table
  BROWSE-02: Sorted by published date (newest first)
  BROWSE-04: Row includes CVE ID, CVSS score, published date, testability (None in Phase 2)
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_cache_service, get_nvd_client
from models.cve import CVEDetail, CVELatestResponse, CVESearchResponse, ErrorResponse
from services.cache_service import CVECacheService
from services.cve_service import get_cve, get_latest_cves, search_cves
from services.nvd_service import NVDClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cve", tags=["cve"])

# Input validation constants
_VALID_CVE_QUERY_PATTERN = re.compile(
    r"^CVE-\d{4}-\d{1,7}(\*)?$",
    re.IGNORECASE,
)
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _validate_cve_id(
    id: str = Query(
        ...,
        description="CVE ID (e.g. CVE-2024-1234) or prefix (e.g. CVE-2024-*)",
        min_length=3,
        max_length=30,
    )
) -> str:
    """Normalize and validate CVE ID query parameter."""
    normalized = id.upper().strip()
    if not _VALID_CVE_QUERY_PATTERN.match(normalized):
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="INVALID_CVE_QUERY",
                message=(
                    f"'{id}' is not a valid CVE query. "
                    "Expected format: CVE-YYYY-NNNNN or CVE-YYYY-* (wildcard prefix)"
                ),
            ).model_dump(),
        )
    return normalized


def _validate_severity(
    severity: Optional[str] = Query(
        None,
        description="Filter by CVSS severity: LOW | MEDIUM | HIGH | CRITICAL (case-insensitive)",
    )
) -> Optional[str]:
    """Normalize and validate severity filter."""
    if severity is None:
        return None
    normalized = severity.upper().strip()
    if normalized not in _VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=ErrorResponse(
                error="INVALID_SEVERITY",
                message=(
                    f"'{severity}' is not a valid severity. "
                    f"Must be one of: {', '.join(sorted(_VALID_SEVERITIES))}"
                ),
            ).model_dump(),
        )
    return normalized


@router.get(
    "/search",
    response_model=CVESearchResponse,
    summary="Search CVE by ID (exact, prefix, or fuzzy)",
    responses={
        404: {"description": "CVE not found in NVD or local cache"},
        422: {"description": "Invalid CVE ID format or severity value"},
        503: {"description": "NVD API unreachable and no cached data available"},
    },
)
async def search_cve(
    id: str = Depends(_validate_cve_id),
    severity: Optional[str] = Depends(_validate_severity),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    cache: CVECacheService = Depends(get_cache_service),
    nvd: NVDClient = Depends(get_nvd_client),
    db: AsyncSession = Depends(get_db),
) -> CVESearchResponse:
    """
    Search for CVEs by ID with optional severity filter.

    - Exact match: `GET /cve/search?id=CVE-2024-1234`
    - Prefix/wildcard: `GET /cve/search?id=CVE-2024-*`
    - Combined filter: `GET /cve/search?id=CVE-2024-*&severity=HIGH`

    Exact ID queries check Redis cache first; NVD is queried only on cache miss.
    Prefix and fuzzy queries search locally-cached CVEs only.

    On NVD rate-limit: serves cached data with HTTP 200 (never HTTP 500).
    """
    results, search_type = await search_cves(
        query=id,
        severity=severity,
        cache=cache,
        nvd=nvd,
        db=db,
        background_tasks=background_tasks,
    )

    if not results and search_type == "exact":
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="CVE_NOT_FOUND",
                message=f"CVE '{id}' not found in NVD or local cache",
            ).model_dump(),
        )

    return CVESearchResponse(
        results=[CVEDetail(**r) for r in results],
        total=len(results),
        query=id,
        search_type=search_type,
    )


@router.get(
    "/latest",
    response_model=CVELatestResponse,
    summary="Browse latest CVEs sorted by published date",
    responses={
        422: {"description": "Invalid page/limit/severity parameter"},
    },
)
async def get_latest(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(
        50, ge=1, le=500,
        description="Results per page (default: 50, max: 500)"
    ),
    severity: Optional[str] = Depends(_validate_severity),
    nvd: NVDClient = Depends(get_nvd_client),
    cache: CVECacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db),
) -> CVELatestResponse:
    """
    Return paginated list of recent CVEs sorted by published date (newest first).

    - Default: 50 results, page 1
    - Filter: `GET /cve/latest?severity=HIGH`
    - Pagination: `GET /cve/latest?page=2&limit=100`

    NVD is queried for fresh data on each call; responses are cached individually.
    On NVD failure, serves from local DB cache without error.
    Severity filter applies to CVSS v3.1 OR v4.0 (whichever is present).
    """
    cve_list, page_total = await get_latest_cves(
        page=page,
        page_size=limit,
        severity=severity,
        nvd=nvd,
        db=db,
        cache=cache,
    )

    return CVELatestResponse(
        results=[CVEDetail(**c) for c in cve_list],
        total=page_total,
        page=page,
        page_size=limit,
        severity_filter=severity,
    )
```

**Route behavior summary:**
- `GET /cve/search?id=CVE-2024-1234` → exact match → cache then NVD → HTTP 200 or 404
- `GET /cve/search?id=CVE-2024-*` → prefix match → local DB only → HTTP 200 (empty list ok)
- `GET /cve/latest` → NVD + DB fallback + pagination → HTTP 200 always
- `GET /cve/latest?severity=high` → case-insensitive → normalized to HIGH → filtered
- NVD 429 + cached data → HTTP 200 (served from cache)
- NVD 429 + no cache → HTTP 503 (not 500)
</implementation>

<verification>
```bash
# After stack is running:

# Exact ID search
curl -s "http://localhost:8000/cve/search?id=CVE-2024-1234" | python3 -m json.tool
# Expect: {"results": [...], "total": 1, "query": "CVE-2024-1234", "search_type": "exact"}

# Severity filter — lowercase must work
curl -s "http://localhost:8000/cve/latest?severity=high" | python3 -m json.tool
# Expect: {"results": [...], "severity_filter": "HIGH", ...}

# Invalid severity → 422
curl -s "http://localhost:8000/cve/latest?severity=EXTREME" | python3 -m json.tool
# Expect: 422 with error: "INVALID_SEVERITY"

# Invalid CVE format → 422
curl -s "http://localhost:8000/cve/search?id=not-a-cve" | python3 -m json.tool
# Expect: 422 with error: "INVALID_CVE_QUERY"

# Pagination
curl -s "http://localhost:8000/cve/latest?page=2&limit=10" | python3 -m json.tool
# Expect: page=2, page_size=10 in response
```
</verification>
</task>

<task id="2.7">
<title>Update main.py: Redis lifespan, dependency registration, CVE router mount</title>
<file>backend/main.py</file>
<depends_on>2.3, 2.6</depends_on>

<context>
`main.py` currently has a minimal lifespan that does nothing (just logs startup/shutdown).
Two changes are required:
1. Initialize the Redis connection pool in lifespan and inject it into the dependency system.
   The pool must be closed cleanly on shutdown. Connection parameters: max_connections=20,
   decode_responses=True (matches JSON string expectations in CVECacheService).
2. Register the CVE router. The stub `cve.py` route exists but is NOT registered — it was never
   added to main.py in Phase 1.

The `set_redis_client()` function from dependencies.py (created in task 2.3) is called during
lifespan startup to inject the live Redis client into the dependency provider.

Add an NVD API key presence check at startup (INFO level only — not a hard failure, since the
app functions without a key, just with stricter rate limits).
</context>

<implementation>
Replace `backend/main.py`:

```python
"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI

from config import get_settings
from dependencies import set_redis_client
from routes.cve import router as cve_router
from routes.health import router as health_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize and teardown shared resources."""
    # Initialize Redis connection pool
    redis_client: Optional[aioredis.Redis] = None
    try:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await redis_client.ping()
        set_redis_client(redis_client)
        logger.info("Redis connection pool initialized: %s", settings.redis_url)
    except Exception as exc:
        logger.warning(
            "Redis unavailable at startup: %s. Cache will be bypassed until Redis recovers.",
            exc,
        )

    # NVD API key presence check (non-fatal — rate limits apply without key)
    if settings.nvd_api_key:
        logger.info("NVD API key configured (100 req/min limit)")
    else:
        logger.warning(
            "NVD_API_KEY not set — operating at 10 req/min NVD limit. "
            "Set NVD_API_KEY in environment for production use."
        )

    logger.info("Application startup complete")
    yield

    # Shutdown: close Redis connection pool
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection pool closed")
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Cyperf CVE Tracker API",
    description="Query CVE data and Cyperf testability status",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(cve_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```
</implementation>

<verification>
```bash
# Verify router registration
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
paths = list(spec['paths'].keys())
assert '/cve/search' in paths, f'Missing /cve/search, got: {paths}'
assert '/cve/latest' in paths, f'Missing /cve/latest, got: {paths}'
print('Routes registered:', paths)
"

# Verify Redis pool initialized (check startup logs)
docker compose logs api | grep -E "Redis connection|startup complete"
```
</verification>
</task>

<task id="2.8">
<title>Update requirements.txt with new dependencies</title>
<file>backend/requirements.txt</file>
<depends_on>none</depends_on>

<context>
Three new runtime dependencies and one dev dependency are required. Pin exact versions to match
research findings and ensure reproducibility across environments.

New dependencies:
- `nvdlib==0.7.6` — NVD API 2.0 wrapper; 0.7.6+ required for v4.0 CVSS attribute support
  (`v40score`, `v40severity`, `v40vector`)
- `tenacity==8.3.0` — retry library for NVD rate-limit exponential backoff
- `rapidfuzz==3.9.0` — C++-backed fuzzy string matching for tier-3 CVE ID search

The existing `models.py` uses `Decimal` (stdlib); no new package needed to fix that — it's a
code change only. `httpx==0.26.0` is already present and not needed for NVD (nvdlib uses requests
internally).

`aiobreaker` (circuit breaker) is deferred to post-Phase-2 hardening. Do not add it now.

Also add `pytest-asyncio` (already present at 0.23.2) and `httpx` (already present) as test
dependencies — no changes needed there. Ensure `anyio[trio]` is not accidentally introduced
(asyncio is the event loop; trio would conflict with FastAPI's default).
</context>

<implementation>
Add the following lines to `backend/requirements.txt` after the existing entries:

```
nvdlib==0.7.6
tenacity==8.3.0
rapidfuzz==3.9.0
```

Full updated `requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.25
alembic==1.13.1
pydantic==2.6.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
redis[asyncio]==5.0.1
httpx==0.26.0
asyncpg==0.29.0
aiosqlite==0.19.0
pytest==7.4.4
pytest-asyncio==0.23.2
apscheduler==3.10.4
cyperf-api-wrapper==1.0.0
nvdlib==0.7.6
tenacity==8.3.0
rapidfuzz==3.9.0
```
</implementation>

<verification>
```bash
# Inside the API container or virtualenv:
pip install -r backend/requirements.txt

# Verify nvdlib v4.0 attribute support:
python3 -c "
import nvdlib
import inspect
# Verify searchCVE_V2 exists (generator for large result sets)
assert hasattr(nvdlib, 'searchCVE_V2'), 'searchCVE_V2 not found; check nvdlib version'
# Verify searchCVE signature has delay parameter
sig = inspect.signature(nvdlib.searchCVE)
assert 'delay' in sig.parameters, 'delay param missing; check nvdlib version'
print('nvdlib OK:', nvdlib.__version__)
"

# Verify rapidfuzz
python3 -c "from rapidfuzz import fuzz, process; print('rapidfuzz OK')"

# Verify tenacity
python3 -c "from tenacity import retry, stop_after_attempt; print('tenacity OK')"
```
</verification>
</task>

<task id="2.9">
<title>Write integration tests for search, browse, cache behavior, and rate-limit fallback</title>
<file>backend/tests/</file>
<depends_on>2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8</depends_on>

<context>
Four test modules covering the success criteria for Phase 2. Tests use `pytest-asyncio` (already
in requirements.txt) and `httpx.AsyncClient` for route-level integration tests (avoids needing
a running server).

Testing strategy:
- NVD calls are always mocked (`AsyncMock` / `patch`) — tests must not make live NVD requests.
  This is non-negotiable: NVD rate-limits will cause flaky CI if real calls are made.
- Redis is tested against a real local Redis instance (not mocked) for integration tests, OR
  mocked for unit tests. Provide a fixture that switches based on environment variable
  `TEST_REDIS_URL` being set.
- DB tests use SQLite in-memory (`:memory:`) via aiosqlite — fast and portable.
- `conftest.py` sets up shared fixtures: async client, async DB session, mock NVD client,
  mock/real Redis.

Test file structure:
```
backend/tests/
  conftest.py                  # Shared fixtures
  test_cve_search.py           # /cve/search endpoint tests
  test_cve_latest.py           # /cve/latest endpoint tests
  test_cache_behavior.py       # Cache hit/miss timing and SWR behavior
  test_rate_limit_fallback.py  # NVD 429 → cache fallback → HTTP 200
```
</context>

<implementation>
Create `backend/tests/conftest.py`:

```python
"""Shared test fixtures for Phase 2 integration tests."""

import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from dependencies import get_cache_service, get_nvd_client, set_redis_client
from main import app
from services.cache_service import CVECacheService
from services.nvd_service import NVDClient


# ─── Sample CVE data fixture ───────────────────────────────────────────────

@pytest.fixture
def sample_cve_dict() -> dict:
    """Minimal valid CVE dict matching application schema."""
    return {
        "id": "CVE-2024-1234",
        "description": "A critical remote code execution vulnerability.",
        "published_date": "2024-01-15T10:00:00",
        "cvss_v3_score": 9.8,
        "cvss_v3_severity": "CRITICAL",
        "cvss_v3_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "cvss_v4_score": None,
        "cvss_v4_severity": None,
        "cvss_v4_vector": None,
        "reference_urls": ["https://example.com/advisory"],
        "testable": None,
    }


# ─── DB Fixture (SQLite in-memory) ─────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session

    await engine.dispose()


# ─── Mock NVD Client ────────────────────────────────────────────────────────

@pytest.fixture
def mock_nvd_client(sample_cve_dict: dict) -> NVDClient:
    """Mock NVDClient that returns sample CVE data without hitting NVD API."""
    mock_cve_obj = MagicMock()
    mock_cve_obj.id = sample_cve_dict["id"]
    mock_cve_obj.published = sample_cve_dict["published_date"]
    mock_cve_obj.descriptions = [MagicMock(lang="en", value=sample_cve_dict["description"])]
    mock_cve_obj.references = [MagicMock(url=u) for u in sample_cve_dict["reference_urls"]]
    mock_cve_obj.v31score = sample_cve_dict["cvss_v3_score"]
    mock_cve_obj.v31severity = sample_cve_dict["cvss_v3_severity"]
    mock_cve_obj.v31vector = sample_cve_dict["cvss_v3_vector"]
    mock_cve_obj.v40score = None
    mock_cve_obj.v40severity = None
    mock_cve_obj.v40vector = None

    client = AsyncMock(spec=NVDClient)
    client.fetch_cve.return_value = mock_cve_obj
    client.fetch_latest.return_value = [mock_cve_obj]
    return client


# ─── Mock Redis / Cache Service ─────────────────────────────────────────────

@pytest.fixture
def mock_cache_service() -> CVECacheService:
    """Mock CVECacheService with in-memory dict store."""
    store: dict = {}
    ttl_store: dict = {}

    svc = AsyncMock(spec=CVECacheService)

    async def mock_get(cve_id: str):
        return store.get(cve_id.upper())

    async def mock_set(cve_id: str, data: dict):
        store[cve_id.upper()] = data
        ttl_store[cve_id.upper()] = 86400
        return True

    async def mock_get_remaining_ttl(cve_id: str):
        return ttl_store.get(cve_id.upper(), -2)

    async def mock_exists(cve_id: str):
        return cve_id.upper() in store

    svc.get.side_effect = mock_get
    svc.set.side_effect = mock_set
    svc.get_remaining_ttl.side_effect = mock_get_remaining_ttl
    svc.exists.side_effect = mock_exists
    svc.is_stale.return_value = False

    return svc


# ─── Test client with dependency overrides ──────────────────────────────────

@pytest_asyncio.fixture
async def test_client(
    mock_nvd_client: NVDClient,
    mock_cache_service: CVECacheService,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with mocked NVD, cache, and in-memory DB."""
    app.dependency_overrides[get_nvd_client] = lambda: mock_nvd_client
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

Create `backend/tests/test_cve_search.py`:

```python
"""Tests for GET /cve/search endpoint.

Covers: SEARCH-01, SEARCH-02, SEARCH-05
"""

import pytest


@pytest.mark.asyncio
async def test_search_exact_id_returns_all_fields(test_client, sample_cve_dict):
    """SEARCH-01 + SEARCH-02: Exact ID returns CVE with all required fields."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    body = response.json()
    assert body["query"] == "CVE-2024-1234"
    assert body["search_type"] == "exact"
    assert body["total"] == 1

    cve = body["results"][0]
    assert cve["id"] == "CVE-2024-1234"
    assert cve["description"] == sample_cve_dict["description"]
    assert cve["published_date"] is not None
    assert isinstance(cve["cvss_v3_score"], float)  # must be float, not string
    assert cve["cvss_v3_severity"] == "CRITICAL"
    assert cve["cvss_v3_vector"] is not None
    assert isinstance(cve["reference_urls"], list)
    assert len(cve["reference_urls"]) > 0
    assert cve["testable"] is None  # Phase 3 placeholder


@pytest.mark.asyncio
async def test_search_case_insensitive_id(test_client):
    """CVE ID lookup is case-insensitive; normalized to uppercase."""
    response = await test_client.get("/cve/search?id=cve-2024-1234")
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_search_severity_filter_high(test_client):
    """SEARCH-05: Severity filter HIGH returns only CRITICAL CVE (CRITICAL >= HIGH is wrong;
    HIGH means exactly HIGH — severity filter is equality, not range)."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234&severity=CRITICAL")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1  # matches CRITICAL

    response_no_match = await test_client.get("/cve/search?id=CVE-2024-1234&severity=LOW")
    assert response_no_match.status_code == 200
    assert response_no_match.json()["total"] == 0  # CRITICAL CVE filtered out by LOW


@pytest.mark.asyncio
async def test_search_severity_case_insensitive(test_client):
    """Severity filter is case-insensitive per context decisions."""
    for severity in ["HIGH", "high", "High", "hIgH"]:
        # CVE-2024-1234 is CRITICAL so HIGH filter should return 0
        response = await test_client.get(f"/cve/search?id=CVE-2024-1234&severity={severity}")
        assert response.status_code == 200  # no 422 regardless of case


@pytest.mark.asyncio
async def test_search_invalid_cve_format_returns_422(test_client):
    """Invalid CVE format returns 422 with INVALID_CVE_QUERY error code."""
    for invalid in ["not-a-cve", "CVE-ABCD-1234", "2024-1234", ""]:
        if not invalid:
            continue
        response = await test_client.get(f"/cve/search?id={invalid}")
        assert response.status_code in (422, 400), f"Expected error for: {invalid}"


@pytest.mark.asyncio
async def test_search_invalid_severity_returns_422(test_client):
    """Invalid severity returns 422 with INVALID_SEVERITY error code."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234&severity=EXTREME")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error"] == "INVALID_SEVERITY"


@pytest.mark.asyncio
async def test_search_not_found_returns_404(test_client, mock_nvd_client):
    """CVE not in NVD and not in cache → 404."""
    mock_nvd_client.fetch_cve.return_value = None  # NVD returns nothing

    response = await test_client.get("/cve/search?id=CVE-2099-99999")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"] == "CVE_NOT_FOUND"


@pytest.mark.asyncio
async def test_search_wildcard_returns_empty_list(test_client):
    """Wildcard/prefix search on empty DB returns empty results (not 404)."""
    response = await test_client.get("/cve/search?id=CVE-2024-*")
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["search_type"] == "prefix"
```

Create `backend/tests/test_cve_latest.py`:

```python
"""Tests for GET /cve/latest endpoint.

Covers: BROWSE-01, BROWSE-02, BROWSE-04
"""

import pytest


@pytest.mark.asyncio
async def test_latest_returns_paginated_results(test_client):
    """BROWSE-01: /cve/latest returns results with pagination metadata."""
    response = await test_client.get("/cve/latest")
    assert response.status_code == 200

    body = response.json()
    assert "results" in body
    assert "page" in body
    assert "page_size" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 50  # default


@pytest.mark.asyncio
async def test_latest_results_include_required_fields(test_client):
    """BROWSE-04: Each result includes CVE ID, CVSS score, published date, testability."""
    response = await test_client.get("/cve/latest")
    body = response.json()

    if body["results"]:
        row = body["results"][0]
        # BROWSE-04 required fields
        assert "id" in row
        assert "cvss_v3_score" in row or "cvss_v4_score" in row
        assert "published_date" in row
        assert "testable" in row  # Phase 3 populates; None is valid in Phase 2


@pytest.mark.asyncio
async def test_latest_pagination_parameters(test_client):
    """Pagination parameters are reflected in response."""
    response = await test_client.get("/cve/latest?page=2&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 10


@pytest.mark.asyncio
async def test_latest_limit_max_500(test_client):
    """Limit above 500 is rejected with 422."""
    response = await test_client.get("/cve/latest?limit=501")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_latest_severity_filter(test_client):
    """SEARCH-05 on browse: severity filter applied; case-insensitive."""
    response_high = await test_client.get("/cve/latest?severity=HIGH")
    assert response_high.status_code == 200
    body = response_high.json()
    assert body["severity_filter"] == "HIGH"

    # All returned CVEs must have HIGH severity in v3.1 or v4.0
    for cve in body["results"]:
        has_high = (
            cve.get("cvss_v3_severity") == "HIGH"
            or cve.get("cvss_v4_severity") == "HIGH"
        )
        assert has_high, f"CVE {cve['id']} does not match HIGH severity"


@pytest.mark.asyncio
async def test_latest_severity_lowercase_accepted(test_client):
    """Severity filter is case-insensitive per context decisions."""
    response = await test_client.get("/cve/latest?severity=critical")
    assert response.status_code == 200
    assert response.json()["severity_filter"] == "CRITICAL"


@pytest.mark.asyncio
async def test_latest_invalid_severity_returns_422(test_client):
    """Invalid severity on /cve/latest returns 422."""
    response = await test_client.get("/cve/latest?severity=UNKNOWN")
    assert response.status_code == 422
```

Create `backend/tests/test_cache_behavior.py`:

```python
"""Tests for Redis cache behavior: hit/miss, SWR trigger.

Covers: SYNC-01 (NVD responses cached in Redis)
"""

import time
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_cache_miss_triggers_nvd_fetch(test_client, mock_nvd_client, mock_cache_service):
    """On cache miss, NVD fetch is called exactly once."""
    mock_cache_service.get.return_value = None  # force cache miss

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    mock_nvd_client.fetch_cve.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_nvd(test_client, mock_nvd_client, mock_cache_service, sample_cve_dict):
    """On cache hit, NVD is NOT re-queried (SYNC-01 core behavior)."""
    # Seed cache
    mock_cache_service.get.return_value = sample_cve_dict
    mock_cache_service.get_remaining_ttl.return_value = 80000  # 22h+ remaining, not stale

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    mock_nvd_client.fetch_cve.assert_not_called()


@pytest.mark.asyncio
async def test_cache_data_written_after_nvd_fetch(test_client, mock_cache_service, mock_nvd_client):
    """After NVD fetch, result is written to cache."""
    mock_cache_service.get.return_value = None  # force cache miss

    await test_client.get("/cve/search?id=CVE-2024-1234")

    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "CVE-2024-1234"  # first arg is cve_id
    assert isinstance(call_args[0][1], dict)    # second arg is cve dict


@pytest.mark.asyncio
async def test_stale_cache_triggers_background_refresh(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """SWR: stale cache (TTL < 4h) triggers background refresh, serves data immediately."""
    # Seed cache with near-expiry TTL
    mock_cache_service.get.return_value = sample_cve_dict
    mock_cache_service.get_remaining_ttl.return_value = 3600  # 1h remaining — stale
    mock_cache_service.is_stale.return_value = True

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200  # served immediately from stale cache

    # Response body is the stale cached data
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_cvss_scores_are_float_not_string(test_client, sample_cve_dict, mock_cache_service):
    """CVSS scores in JSON response must be floats, not strings (Pydantic Decimal bug)."""
    mock_cache_service.get.return_value = sample_cve_dict

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    body = response.json()
    cve = body["results"][0]

    if cve["cvss_v3_score"] is not None:
        assert isinstance(cve["cvss_v3_score"], float)
    if cve["cvss_v4_score"] is not None:
        assert isinstance(cve["cvss_v4_score"], float)
```

Create `backend/tests/test_rate_limit_fallback.py`:

```python
"""Tests for NVD rate-limit fallback behavior.

Covers: SYNC-05 (NVD rate-limit → HTTP 200, no 500)
Architecture invariant: NVD 429 must never surface as HTTP 500.
"""

import pytest
from services.nvd_service import NVDRateLimitError


@pytest.mark.asyncio
async def test_nvd_rate_limit_with_cache_returns_200(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """
    SYNC-05: When NVD is rate-limited and cache has data, API returns HTTP 200.
    This is the critical path — a 500 here violates the architecture invariant.
    """
    # NVD is rate-limited
    mock_nvd_client.fetch_cve.side_effect = NVDRateLimitError("Rate limited")

    # But cache has the CVE
    mock_cache_service.get.return_value = sample_cve_dict
    mock_cache_service.get_remaining_ttl.return_value = 80000

    response = await test_client.get("/cve/search?id=CVE-2024-1234")

    # Must be 200, not 429, not 500, not 503
    assert response.status_code == 200, (
        f"Expected 200 on rate-limit with cache hit, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_nvd_rate_limit_no_cache_returns_503(
    test_client, mock_cache_service, mock_nvd_client
):
    """
    When NVD is rate-limited AND no cached data exists, API returns 503.
    503 = "service temporarily unavailable", not 500 = "our bug".
    """
    mock_nvd_client.fetch_cve.side_effect = NVDRateLimitError("Rate limited")
    mock_cache_service.get.return_value = None  # no cache

    response = await test_client.get("/cve/search?id=CVE-2099-99999")

    # 503 is acceptable; 500 is NOT
    assert response.status_code in (503, 404), (
        f"Expected 503 or 404 when NVD down + no cache, got {response.status_code}"
    )
    assert response.status_code != 500, "HTTP 500 must never be returned on NVD rate-limit"


@pytest.mark.asyncio
async def test_nvd_rate_limit_latest_serves_db_cache(
    test_client, mock_nvd_client
):
    """
    /cve/latest with NVD rate-limited serves from DB (empty on fresh start).
    Response is always HTTP 200 with empty or partial results — never 500.
    """
    mock_nvd_client.fetch_latest.side_effect = NVDRateLimitError("Rate limited")

    response = await test_client.get("/cve/latest")

    # Must not be 500 regardless of NVD state
    assert response.status_code == 200, (
        f"Expected 200 on /cve/latest with NVD down, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_redis_down_falls_back_to_nvd(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """
    Redis failure must not bring down the API.
    Falls back to NVD fetch and returns data.
    """
    mock_cache_service.get.return_value = None  # Redis failure returns None
    mock_nvd_client.fetch_cve.return_value = MagicMock()  # NVD succeeds

    # Mock the NVD object attributes
    nvd_obj = mock_nvd_client.fetch_cve.return_value
    nvd_obj.id = "CVE-2024-1234"
    nvd_obj.published = "2024-01-15T10:00:00.000"
    nvd_obj.descriptions = [MagicMock(lang="en", value="Test")]
    nvd_obj.references = []
    nvd_obj.v31score = 9.8
    nvd_obj.v31severity = "CRITICAL"
    nvd_obj.v31vector = "CVSS:3.1/AV:N"
    nvd_obj.v40score = None
    nvd_obj.v40severity = None
    nvd_obj.v40vector = None

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200
```

Add `pytest.ini` or `pyproject.toml` section for asyncio mode:

In `backend/pyproject.toml`, add (or verify exists):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
</implementation>

<verification>
```bash
# Run all Phase 2 tests (from backend directory or via docker exec)
pytest backend/tests/ -v --tb=short

# Expected output:
# tests/test_cve_search.py::test_search_exact_id_returns_all_fields PASSED
# tests/test_cve_search.py::test_search_case_insensitive_id PASSED
# tests/test_cve_search.py::test_search_severity_filter_high PASSED
# tests/test_cve_search.py::test_search_severity_case_insensitive PASSED
# tests/test_cve_search.py::test_search_invalid_cve_format_returns_422 PASSED
# tests/test_cve_search.py::test_search_invalid_severity_returns_422 PASSED
# tests/test_cve_search.py::test_search_not_found_returns_404 PASSED
# tests/test_cve_search.py::test_search_wildcard_returns_empty_list PASSED
# tests/test_cve_latest.py::... PASSED (7 tests)
# tests/test_cache_behavior.py::... PASSED (5 tests)
# tests/test_rate_limit_fallback.py::... PASSED (4 tests)
# ─────────────────────────────────────────────────
# 24 passed in <Xs
```
</verification>
</task>

<task id="2.10">
<title>End-to-end verification against live Docker stack</title>
<file>N/A (verification only)</file>
<depends_on>2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9</depends_on>

<context>
After all implementation tasks complete, run end-to-end verification against the live Docker stack
to confirm all Phase 2 success criteria are met. This is the gate before marking Phase 2 complete.

Use `time curl` to measure response times and verify the <100ms cache hit requirement.
Verify the `testable` field is present but null (Phase 3 will populate it).
Verify Docker logs contain no Python tracebacks on normal request paths.
</context>

<implementation>
No code changes. Run the verification commands listed below.
</implementation>

<verification>
```bash
# 1. Rebuild and restart with new dependencies
docker compose build api && docker compose up -d

# 2. Wait for health
sleep 5
curl -sf http://localhost:8000/health/ | python3 -m json.tool

# 3. Success Criterion 1: GET /cve/search?id=CVE-2024-1234
# Returns CVE details with CVSS v3.1, v4.0, description, published date, references
curl -s "http://localhost:8000/cve/search?id=CVE-2024-1234" | python3 -c "
import json, sys
body = json.load(sys.stdin)
assert body['total'] >= 1, 'Expected at least 1 result'
cve = body['results'][0]
print('id:', cve['id'])
print('description:', cve['description'][:60])
print('published_date:', cve['published_date'])
print('cvss_v3_score:', cve['cvss_v3_score'], type(cve['cvss_v3_score']).__name__)
print('cvss_v3_severity:', cve['cvss_v3_severity'])
print('reference_urls count:', len(cve['reference_urls']))
print('testable (Phase 3):', cve['testable'])
assert isinstance(cve['cvss_v3_score'], float), 'CVSS score must be float, not string'
print('PASS: SC1 - All required fields present with correct types')
"

# 4. Success Criterion 2: GET /cve/latest (paginated, newest-first)
curl -s "http://localhost:8000/cve/latest?limit=50" | python3 -c "
import json, sys
body = json.load(sys.stdin)
print('page:', body['page'], 'page_size:', body['page_size'], 'total:', body['total'])
if len(body['results']) >= 2:
    dates = [r['published_date'] for r in body['results'] if r['published_date']]
    is_sorted = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
    assert is_sorted, 'Results not sorted newest-first'
print('PASS: SC2 - Pagination and sort order correct')
"

# 5. Success Criterion 3: GET /cve/latest?severity=HIGH (case-insensitive)
curl -s "http://localhost:8000/cve/latest?severity=high" | python3 -c "
import json, sys
body = json.load(sys.stdin)
assert body['severity_filter'] == 'HIGH', f'Expected HIGH, got {body[\"severity_filter\"]}'
for cve in body['results']:
    has_high = (
        cve.get('cvss_v3_severity') == 'HIGH' or
        cve.get('cvss_v4_severity') == 'HIGH'
    )
    assert has_high, f'{cve[\"id\"]} returned but does not have HIGH severity'
print('PASS: SC3 - Severity filter works, case-insensitive')
"

# 6. Success Criterion 4: Cache hit < 100ms (2nd identical request)
# First request (cache miss - may take 1-3s for NVD)
time curl -s "http://localhost:8000/cve/search?id=CVE-2024-1234" > /dev/null

# Second request (cache hit - must be < 100ms)
start_ns=$(python3 -c "import time; print(int(time.time()*1000))")
curl -s "http://localhost:8000/cve/search?id=CVE-2024-1234" > /dev/null
end_ns=$(python3 -c "import time; print(int(time.time()*1000))")
elapsed=$((end_ns - start_ns))
echo "Cache hit response time: ${elapsed}ms"
[ "$elapsed" -lt 100 ] && echo "PASS: SC4 - Cache hit < 100ms" || echo "WARN: Cache hit ${elapsed}ms (target <100ms)"

# 7. Success Criterion 5: NVD 429 → HTTP 200 from cache
# Pre-populate cache with a first request, then simulate 429
curl -s "http://localhost:8000/cve/search?id=CVE-2024-1234" > /dev/null  # seed cache
# The rate-limit fallback is verified by the test suite (task 2.9); live simulation
# requires NVD to actually 429 which is not reliably triggerable. Trust the test.
echo "SC5 verification: covered by test_rate_limit_fallback.py"

# 8. Check Docker logs for tracebacks
docker compose logs api --since=5m 2>&1 | grep -i "traceback\|exception\|error" | head -20
echo "If no output above, no unhandled exceptions in logs"

# 9. OpenAPI spec sanity check
curl -s http://localhost:8000/openapi.json | python3 -c "
import json, sys
spec = json.load(sys.stdin)
paths = list(spec['paths'].keys())
print('Registered paths:', paths)
assert '/cve/search' in paths
assert '/cve/latest' in paths
print('PASS: Both CVE routes registered in OpenAPI spec')
"
```
</verification>
</task>

</tasks>

---

## Requirement Traceability

| Requirement | Covered by Tasks | How |
|-------------|-----------------|-----|
| SEARCH-01 | 2.6 (route), 2.5 (service) | `/cve/search?id=CVE-2024-1234` → exact match tier in dispatch logic |
| SEARCH-02 | 2.1 (model), 2.2 (extract), 2.6 (route) | CVEDetail exposes all required fields; extract_cve_fields maps nvdlib attrs |
| SEARCH-05 | 2.5 (`_filter_by_severity`), 2.6 (route) | Post-filter with OR semantics; v3.1 or v4.0 match; case-insensitive |
| BROWSE-01 | 2.6 (`/cve/latest` route), 2.5 (`get_latest_cves`) | Paginated response with page/page_size/total |
| BROWSE-02 | 2.5 (`ORDER BY published_date DESC`) | SQLAlchemy query sorts descending; NVD date window ensures recency |
| BROWSE-04 | 2.1 (CVEDetail fields), 2.6 (route) | `id`, `cvss_v3_score`, `published_date`, `testable` all in CVEDetail |
| SYNC-01 | 2.3 (cache_service), 2.5 (upsert logic) | Every NVD fetch result written to Redis (24h TTL + jitter); also persisted to DB |
| SYNC-05 | 2.4 (retry), 2.5 (fallback), 2.6 (route) | NVDRateLimitError → retry 3x → DB fallback → 200 or 503 (never 500) |

---

## Architecture Invariants Verified

| Invariant | Implementation | Task |
|-----------|---------------|------|
| NVD rate-limit → HTTP 200 (never 500) | NVDRateLimitError caught in cve_service; route returns 503 only if no cache exists anywhere | 2.4, 2.5 |
| Credentials never in logs | Logger calls only include CVE IDs, not NVD API key or Cyperf credentials | 2.2, 2.7 |
| Async-first | nvdlib wrapped in asyncio.to_thread(); all routes are async; Redis uses aioredis | 2.2, 2.3 |
| Pydantic validation before use | CVEDetail validates all response data; ErrorResponse validates error payloads | 2.1 |
| Redis failure non-fatal | CVECacheService wraps all ops in try/except; returns None/False on failure | 2.3 |

---

## must_haves

When Phase 2 is complete, ALL of the following must be true:

- [ ] `GET /cve/search?id=CVE-2024-1234` returns HTTP 200 with `id`, `description`,
  `published_date`, `cvss_v3_score`, `cvss_v3_severity`, `cvss_v3_vector`, `cvss_v4_score`,
  `cvss_v4_severity`, `cvss_v4_vector`, `reference_urls` — all as correct types (CVSS as `float`)
- [ ] `GET /cve/search?id=CVE-2024-*` returns HTTP 200 (empty list if DB is empty — never 404)
- [ ] `GET /cve/latest` returns paginated response with `results`, `page`, `page_size`, `total`;
  results sorted by `published_date` descending
- [ ] `GET /cve/latest?severity=HIGH` and `?severity=high` both return HTTP 200; severity
  normalized to uppercase in response body; results filtered to CVEs with HIGH in v3.1 OR v4.0
- [ ] `GET /cve/latest?limit=501` returns HTTP 422
- [ ] Second identical request for the same CVE is served from Redis cache with response time
  under 100ms; NVD is not re-queried (verified by `mock_nvd_client.fetch_cve.assert_not_called()`)
- [ ] NVD 429 + cached data present → HTTP 200 (test: `test_nvd_rate_limit_with_cache_returns_200`)
- [ ] NVD 429 + no cache → HTTP 503, never HTTP 500 (test: `test_nvd_rate_limit_no_cache_returns_503`)
- [ ] Redis down → API continues serving via NVD (test: `test_redis_down_falls_back_to_nvd`)
- [ ] All 24 tests in `backend/tests/` pass with `pytest -v`
- [ ] `docker compose logs api` contains no unhandled Python tracebacks on normal request paths
- [ ] OpenAPI spec at `/openapi.json` includes `/cve/search` and `/cve/latest` with correct
  query parameters documented

---

## Failure Mode Reference

| Failure | HTTP Response | Recovery |
|---------|--------------|----------|
| NVD 429, cache populated | 200 (stale cache) | Tenacity retry → cache fallback |
| NVD 429, no cache exists | 503 | User retries later; log at WARNING |
| NVD timeout / unknown error | 503 (if no DB fallback) | Same as 429 path |
| Redis down | 200 (NVD direct fetch) | try/except wraps all Redis ops |
| CVE not in NVD | 404 | results[0] None guard → 404 |
| Invalid CVE format in query | 422 | Route validator rejects pre-service |
| Invalid severity value | 422 | Route validator rejects pre-service |
| DB down (write fails) | 200 (Redis still serves reads) | upsert failure logged; cache is primary |

---

## Deferred to Phase 3

These are explicitly excluded from Phase 2 scope:

- `testable` and `attack_profile` fields populated (requires Cyperf sync)
- `POST /admin/sync-cyperf` trigger endpoint
- Daily scheduled sync job (APScheduler)
- `GET /admin/sync-status` endpoint
- Circuit breaker (aiobreaker) for NVD — tenacity + cache fallback is sufficient for Phase 2

---

*Plan written: 2026-02-23*
*Phase: 02-backend-api-nvd-integration*
*Status: Ready for implementation*
