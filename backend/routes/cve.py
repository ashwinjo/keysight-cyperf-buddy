"""CVE search and browse endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db.cyperf_mapping import CyperfSupportedCVE
from models import CVEResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cve", tags=["cve"])


async def get_cyperf_testability(session: AsyncSession, cve_id: str) -> tuple[bool, str | None]:
    """Check if CVE is testable with Cyperf and get profile name.

    Args:
        session: AsyncSession for database queries
        cve_id: CVE identifier (e.g. CVE-2024-1234)

    Returns:
        Tuple of (testable: bool, attack_profile: Optional[str])
        Returns (False, None) if CVE not testable or database error
    """
    try:
        stmt = select(CyperfSupportedCVE).where(CyperfSupportedCVE.cve_id == cve_id)
        result = await session.execute(stmt)
        record = result.scalars().first()

        if record:
            return (True, record.attack_profile_name)
        return (False, None)

    except Exception as e:
        # Log error but don't fail the request
        logger.warning(f"Error checking testability for {cve_id}: {e}")
        return (False, None)


@router.get("/search")
async def search_cve(
    id: str = Query(..., description="CVE ID (e.g. CVE-2024-1234)"),
    session: AsyncSession = None,
) -> CVEResponse:
    """Search for CVE by exact ID.

    Returns CVE details from NVD including CVSS scores, description, and references.
    Also includes testability status from Cyperf sync.

    Phase 2 implements NVD integration; Phase 3 adds testability fields.

    Query Parameters:
        id: CVE identifier (required)

    Returns:
        CVEResponse with NVD data + testability fields

    Raises:
        HTTPException 404: If CVE not found in NVD
        HTTPException 500: Unexpected errors

    Note:
        This is a stub pending Phase 2 NVD integration.
        Testability fields (testable, attack_profile) are phase 3 additions.
    """
    if not session:
        async for s in get_db():
            session = s
            break

    try:
        # PHASE 2: Query NVD cache for CVE details
        # TODO: Implement NVD query logic in Phase 2
        # For now, return stub response with testability fields

        # PHASE 3: Query Cyperf testability
        testable, profile = await get_cyperf_testability(session, id)

        # Return minimal response with testability
        # Phase 2 will populate NVD fields
        return CVEResponse(
            id=id,
            description="[NVD data pending Phase 2]",
            published_date=None,
            last_modified=None,
            cvss_v3_vector=None,
            cvss_v3_score=None,
            cvss_v3_severity=None,
            cvss_v4_vector=None,
            cvss_v4_score=None,
            cvss_v4_severity=None,
            references=None,
            testable=testable,
            attack_profile=profile,
        )

    except Exception as e:
        logger.error(f"Error searching for CVE {id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}",
        )


@router.get("/latest")
async def get_latest_cves() -> dict:
    """Get latest CVEs (stub for Phase 2)."""
    return {"status": "coming in phase 2"}
