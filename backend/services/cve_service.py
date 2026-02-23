"""CVE orchestration service.

Implements cache-aside + stale-while-revalidate + NVD rate-limit fallback.
All public methods are safe to call from FastAPI routes — they do not raise
infrastructure exceptions; they return None on total failure.

Architecture:
- Cache-aside with SWR: check cache first, trigger background refresh if stale
- Rate-limit fallback (SYNC-05): NVD 429 -> DB fallback -> None (route returns 503)
- Fuzzy search dispatch: exact -> SQL LIKE prefix -> RapidFuzz (local DB only)
- DB persistence: every NVD fetch is written to cves table via upsert
- Severity post-filter: OR semantics (v3.1 OR v4.0 match)
"""

import json
import logging
import re
from datetime import datetime

from fastapi import BackgroundTasks
from rapidfuzz import fuzz, process
from sqlalchemy import select
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
) -> dict | None:
    """Fetch a single CVE by exact ID with full cache-aside + SWR + fallback.

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
            background_tasks.add_task(_background_refresh_cve, normalized_id, cache, nvd, db)
        return cached

    # 2. Cache miss: attempt NVD fetch with retry + fallback
    return await _fetch_and_cache(normalized_id, cache, nvd, db)


async def search_cves(
    query: str,
    severity: str | None,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
) -> tuple[list[dict], str]:
    """Dispatch CVE search across 3 tiers: exact -> prefix -> fuzzy.

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
    severity: str | None,
    nvd: NVDClient,
    db: AsyncSession,
    cache: CVECacheService,
) -> tuple[list[dict], int]:
    """Fetch latest CVEs sorted by published date (newest first).

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
        logger.warning("NVD rate-limited during /cve/latest fetch; serving from DB cache")
    except Exception as exc:
        logger.error("NVD fetch failed for /cve/latest: %s", exc, exc_info=True)

    # Step 2: Query DB with pagination
    offset = (page - 1) * page_size
    stmt = select(CVE).order_by(CVE.published_date.desc()).offset(offset).limit(page_size)
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
) -> dict | None:
    """Fetch CVE from NVD (with retry), write to cache + DB.

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
        logger.warning("NVD rate-limited after retries for %s; checking DB fallback", cve_id)
        return await _get_from_db(cve_id, db)

    except Exception as exc:
        logger.error("Unexpected NVD fetch error for %s: %s", cve_id, exc, exc_info=True)
        return await _get_from_db(cve_id, db)


async def _background_refresh_cve(
    cve_id: str,
    cache: CVECacheService,
    nvd: NVDClient,
    db: AsyncSession,
) -> None:
    """Background task: refresh a near-expired CVE from NVD.

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
    """SQL LIKE search against CVE IDs in the local database.

    Translates * wildcards to SQL % wildcards.
    Only searches locally-cached CVEs, not NVD live.
    """
    sql_pattern = query.replace("*", "%")
    stmt = (
        select(CVE).where(CVE.id.like(sql_pattern)).order_by(CVE.published_date.desc()).limit(limit)
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
    """RapidFuzz token_sort_ratio match against locally-cached CVE IDs.

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
    """Filter CVEs by severity using OR semantics: v3.1 OR v4.0 must match.

    Per context decision: case-insensitive, OR not AND.
    """
    return [
        c
        for c in cves
        if (c.get("cvss_v3_severity") or "").upper() == severity
        or (c.get("cvss_v4_severity") or "").upper() == severity
    ]


async def _upsert_cve(cve_data: dict, db: AsyncSession) -> None:
    """Upsert CVE into the database.

    Uses merge pattern (compatible with both SQLite and PostgreSQL via SQLAlchemy 2.0).
    references field is JSON-encoded for the TEXT DB column.
    Converts published_date ISO string to datetime object for DateTime column.
    """
    references_json = json.dumps(cve_data.get("reference_urls", []))

    # Convert published_date from ISO string to datetime if present
    published_date = None
    if cve_data.get("published_date"):
        try:
            published_date = datetime.fromisoformat(cve_data["published_date"])
        except (ValueError, TypeError):
            published_date = None

    existing = await db.get(CVE, cve_data["id"])
    if existing is None:
        db.add(
            CVE(
                id=cve_data["id"],
                description=cve_data.get("description"),
                published_date=published_date,
                cvss_v3_score=cve_data.get("cvss_v3_score"),
                cvss_v3_severity=cve_data.get("cvss_v3_severity"),
                cvss_v3_vector=cve_data.get("cvss_v3_vector"),
                cvss_v4_score=cve_data.get("cvss_v4_score"),
                cvss_v4_severity=cve_data.get("cvss_v4_severity"),
                cvss_v4_vector=cve_data.get("cvss_v4_vector"),
                references=references_json,
            )
        )
    else:
        # Update all fields except id and first_seen
        existing.description = cve_data.get("description")
        existing.published_date = published_date
        existing.cvss_v3_score = cve_data.get("cvss_v3_score")
        existing.cvss_v3_severity = cve_data.get("cvss_v3_severity")
        existing.cvss_v3_vector = cve_data.get("cvss_v3_vector")
        existing.cvss_v4_score = cve_data.get("cvss_v4_score")
        existing.cvss_v4_severity = cve_data.get("cvss_v4_severity")
        existing.cvss_v4_vector = cve_data.get("cvss_v4_vector")
        existing.references = references_json


async def _get_from_db(cve_id: str, db: AsyncSession) -> dict | None:
    """Last-resort fallback: query DB for CVE. Used when NVD is unreachable.

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

    published_str: str | None = None
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
