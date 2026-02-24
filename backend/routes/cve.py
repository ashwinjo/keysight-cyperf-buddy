"""CVE search and browse endpoints.

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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_cache_service, get_nvd_client
from models.cve import CVEDetail, CVELatestResponse, CVESearchResponse, ErrorResponse
from services.cache_service import CVECacheService
from services.cve_service import get_latest_cves, search_cves
from services.nvd_service import NVDClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cve", tags=["cve"])

# Input validation constants
_VALID_CVE_QUERY_PATTERN = re.compile(
    r"^CVE-\d{4}-(\d{1,7}|\*)$",
    re.IGNORECASE,
)
_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _validate_cve_id(
    id: str = Query(
        ...,
        description="CVE ID (e.g. CVE-2024-1234) or prefix (e.g. CVE-2024-*)",
        min_length=3,
        max_length=30,
    ),
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
    severity: str | None = Query(
        None,
        description="Filter by CVSS severity: LOW | MEDIUM | HIGH | CRITICAL (case-insensitive)",
    ),
) -> str | None:
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
    severity: str | None = Depends(_validate_severity),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    cache: CVECacheService = Depends(get_cache_service),
    nvd: NVDClient = Depends(get_nvd_client),
    db: AsyncSession = Depends(get_db),
) -> CVESearchResponse:
    """Search for CVEs by ID with optional severity filter.

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

    # Return 404 only if:
    # - search_type is "exact" (direct ID lookup)
    # - no results AND no severity filter (if severity is applied, CVE may exist but not match severity)
    if not results and search_type == "exact" and not severity:
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
    limit: int = Query(50, ge=1, le=2500, description="Results per page (default: 50, max: 2500)"),
    severity: str | None = Depends(_validate_severity),
    nvd: NVDClient = Depends(get_nvd_client),
    cache: CVECacheService = Depends(get_cache_service),
    db: AsyncSession = Depends(get_db),
) -> CVELatestResponse:
    """Return paginated list of recent CVEs sorted by published date (newest first).

    - Default: 50 results, page 1
    - Get all: `GET /cve/latest?limit=2500` (returns all 2195 CVEs)
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
