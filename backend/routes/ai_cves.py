"""GET /ai-cves — paginated list of AI-type strike records from the ai_cves table.

The Vite dev proxy rewrites /api/* -> http://localhost:8000/* so this router,
registered at prefix /ai-cves, is reachable at /api/ai-cves from the frontend.

Supported query parameters:
  page        int  >= 1           Page number, 1-indexed (default: 1)
  limit       int  1..10000       Records per page (default: 100, max: 10000)
  strike_type str  optional       Filter by AICve.strike_type exact match
                                  (e.g. 'ai_attack', 'fuzzing', 'protocol_abuse')
  ai_only     bool optional       Filter to only AI strikes (URL refs, <3 refs)
"""

import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db.ai_cves import AICve
from models.ai_cve import AiCVEListResponse, AiCVEResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-cves", tags=["ai-cves"])


def _is_ai_strike(metadata_json: str | None) -> bool:
    """Check if a strike is an AI strike based on metadata.

    AI strikes have:
    - metadata_json is not None
    - Less than 3 references
    - At least one reference with Type='url'
    """
    if not metadata_json:
        return False

    try:
        refs = json.loads(metadata_json)
        if not isinstance(refs, list) or len(refs) >= 3:
            return False

        # Check if at least one ref has Type='url'
        return any(ref.get("Type") == "url" for ref in refs)
    except (json.JSONDecodeError, TypeError):
        return False


@router.get("", response_model=AiCVEListResponse)
async def list_ai_cves(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(100, ge=1, le=10000, description="Records per page (max 10000)"),
    strike_type: str | None = Query(
        None,
        description="Filter by strike category (e.g. ai_attack, fuzzing, protocol_abuse)",
    ),
    ai_only: bool = Query(
        False,
        description="Filter to only AI strikes (those with URL references and <3 refs)",
    ),
    session: AsyncSession = Depends(get_db),
) -> AiCVEListResponse:
    """Return a paginated list of AI CVE records from the ai_cves table.

    Records are ordered by created_at DESC (newest first).
    Optional strike_type filter performs an exact-match WHERE clause.

    Returns:
        AiCVEListResponse with results list and unpaged total count.
    """
    # Build base WHERE clause (shared between count and data queries)
    base_filter = AICve.strike_type == strike_type if strike_type is not None else None

    # COUNT query — unpaged total for client-side pagination UI
    count_stmt = select(func.count()).select_from(AICve)
    if base_filter is not None:
        count_stmt = count_stmt.where(base_filter)

    count_result = await session.execute(count_stmt)
    total: int = count_result.scalar_one()

    # Data query — paginated, newest first
    offset = (page - 1) * limit
    data_stmt = select(AICve).order_by(AICve.created_at.desc()).offset(offset).limit(limit)
    if base_filter is not None:
        data_stmt = data_stmt.where(base_filter)

    data_result = await session.execute(data_stmt)
    rows = data_result.scalars().all()

    # Post-filter for AI strikes if requested
    if ai_only:
        rows = [row for row in rows if _is_ai_strike(row.metadata_json)]
        # Recalculate total after AI filtering
        all_rows_stmt = select(AICve)
        if base_filter is not None:
            all_rows_stmt = all_rows_stmt.where(base_filter)
        all_rows_result = await session.execute(all_rows_stmt)
        all_rows = all_rows_result.scalars().all()
        total = len([row for row in all_rows if _is_ai_strike(row.metadata_json)])

    results = [AiCVEResponse.from_orm_row(row) for row in rows]

    logger.debug(
        "GET /ai-cves: page=%d limit=%d strike_type=%r ai_only=%s -> %d/%d records",
        page,
        limit,
        strike_type,
        ai_only,
        len(results),
        total,
    )

    return AiCVEListResponse(results=results, total=total)
