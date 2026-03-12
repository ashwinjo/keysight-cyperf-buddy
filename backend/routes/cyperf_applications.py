"""API endpoints for Cyperf applications and application types."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from db.cverf_cve_strike_mappings import CvrfCveStrikeMappings
from db.cyperf_application import CyperfApplication
from db.cyperf_application_type import CyperfApplicationType
from models.cyperf_applications import (
    CyperfApplicationListResponse,
    CyperfApplicationResponse,
    CyperfApplicationTypeListResponse,
    CyperfApplicationTypeResponse,
    CyperfStrikeListResponse,
    CyperfStrikeResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cyperf-applications", tags=["cyperf-applications"])


@router.get("/types", response_model=CyperfApplicationTypeListResponse)
async def get_application_types(
    session: AsyncSession = Depends(get_db),
) -> CyperfApplicationTypeListResponse:
    """Get all Cyperf application types.

    Returns paginated list of application types from the database.
    """
    # Get all application types
    stmt = select(CyperfApplicationType).order_by(CyperfApplicationType.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    results = [
        CyperfApplicationTypeResponse(
            id=row.id,
            name=row.name,
            description=row.description,
        )
        for row in rows
    ]

    logger.debug(f"GET /cyperf-applications/types -> {len(results)} records")

    return CyperfApplicationTypeListResponse(results=results, total=len(results))


@router.get("/strikes", response_model=CyperfStrikeListResponse)
async def get_strikes(
    session: AsyncSession = Depends(get_db),
) -> CyperfStrikeListResponse:
    """Get all distinct Cyperf strike names from CVE-Strike mappings.

    Returns distinct strike names stored in cverf_cve_strike_mappings table.
    Used by the L4-7 Test Advisor agent for recommendation matching.
    """
    stmt = (
        select(CvrfCveStrikeMappings.strike_name)
        .distinct()
        .order_by(CvrfCveStrikeMappings.strike_name)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    results = [CyperfStrikeResponse(strike_name=name) for name in rows]
    logger.debug(f"GET /cyperf-applications/strikes -> {len(results)} distinct strikes")

    return CyperfStrikeListResponse(results=results, total=len(results))


@router.get("", response_model=CyperfApplicationListResponse)
async def get_applications(
    session: AsyncSession = Depends(get_db),
) -> CyperfApplicationListResponse:
    """Get all Cyperf applications.

    Returns paginated list of applications from the database.
    """
    # Get all applications
    stmt = select(CyperfApplication).order_by(CyperfApplication.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    results = [
        CyperfApplicationResponse(
            id=row.id,
            name=row.name,
            description=row.description,
        )
        for row in rows
    ]

    logger.debug(f"GET /cyperf-applications -> {len(results)} records")

    return CyperfApplicationListResponse(results=results, total=len(results))
