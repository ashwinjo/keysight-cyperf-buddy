"""Admin endpoints for Cyperf sync status and manual triggering."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from db.cyperf_mapping import CyperfSupportedCVE
from db.sync_metadata import SyncMetadata
from models import SyncStatusResponse
from scheduler import trigger_cyperf_sync_now
from services.sync_service import perform_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/sync-status")
async def get_sync_status(session: AsyncSession = Depends(get_db)) -> SyncStatusResponse:
    """Get current Cyperf sync status and metadata.

    Returns detailed information about the last sync attempt, including:
    - When it ran and when it completed
    - Current status (success, failed, running, never)
    - Number of profiles and CVEs synced
    - Error message if failed
    - When next sync is scheduled

    Returns:
        SyncStatusResponse with all metadata fields populated or nulled gracefully

    Note:
        This endpoint never returns errors (HTTP 200). If database query fails,
        it returns status='failed' with error_message set.

        Authentication: TODO - Add auth middleware in Phase 4
    """
    try:
        # Query for cyperf_profiles sync metadata
        metadata = await SyncMetadata.get_last_sync_status(session, job_name="cyperf_profiles")

        if not metadata:
            # Never synced; return status='never' with null timestamps
            return SyncStatusResponse(
                last_successful_sync=None,
                last_attempted_sync=None,
                sync_status="never",
                cverf_profiles_synced=0,
                cverf_cves_extracted=0,
                error_message=None,
                next_scheduled_sync=None,
            )

        # Count CVEs currently in database (as of this sync)
        stmt = select(CyperfSupportedCVE)
        result = await session.execute(stmt)
        cves_count = len(result.scalars().all())

        return SyncStatusResponse(
            last_successful_sync=(
                metadata.last_completed_at.isoformat() + "Z" if metadata.last_completed_at else None
            ),
            last_attempted_sync=(
                metadata.last_run_at.isoformat() + "Z" if metadata.last_run_at else None
            ),
            sync_status=metadata.status or "never",
            cverf_profiles_synced=metadata.profiles_synced or 0,
            cverf_cves_extracted=cves_count,
            error_message=metadata.error_message,
            next_scheduled_sync=(
                metadata.next_scheduled_run.isoformat() + "Z"
                if metadata.next_scheduled_run
                else None
            ),
        )

    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        # Return degraded response instead of 500
        return SyncStatusResponse(
            last_successful_sync=None,
            last_attempted_sync=None,
            sync_status="failed",
            cverf_profiles_synced=0,
            cverf_cves_extracted=0,
            error_message=f"Database error: {str(e)}",
            next_scheduled_sync=None,
        )


@router.post("/sync-cyperf")
async def trigger_manual_sync(session: AsyncSession = Depends(get_db)) -> dict:
    """Trigger an immediate Cyperf sync (manual trigger for testing/emergency).

    Queues an immediate one-time sync job outside the normal 24-hour schedule.
    Useful for development/testing or if Cyperf was unreachable and needs immediate retry.

    Returns:
        HTTP 202 Accepted with status="sync_triggered" message

    Raises:
        HTTPException 500: If scheduler is not running

    Note:
        This endpoint returns immediately (async); the actual sync happens in background.
        To check status, call GET /admin/sync-status after sync completes.

        Authentication: TODO - Add auth middleware in Phase 4
    """
    try:
        settings = get_settings()

        # Option B (recommended): Queue manual sync job to scheduler
        # This ensures consistency with scheduled jobs
        try:
            trigger_cyperf_sync_now()
            logger.info("Manual sync triggered via POST /admin/sync-cyperf")

            return {
                "status": "sync_triggered",
                "message": "Cyperf sync queued for immediate execution",
            }

        except Exception:
            # Scheduler might not be running; fall back to direct execution
            logger.warning("Scheduler not running; executing sync directly")

            # Option A (fallback): Call perform_sync directly
            await perform_sync(session=session, settings=settings)

            return {
                "status": "sync_completed",
                "message": "Cyperf sync completed immediately",
            }

    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger sync: {str(e)}",
        )
