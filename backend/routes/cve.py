"""CVE search and browse endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/cve", tags=["cve"])


@router.get("/search")
async def search_cve() -> dict:
    """Search for CVEs (stub for Phase 2)."""
    return {"status": "coming in phase 2"}


@router.get("/latest")
async def get_latest_cves() -> dict:
    """Get latest CVEs (stub for Phase 2)."""
    return {"status": "coming in phase 2"}
