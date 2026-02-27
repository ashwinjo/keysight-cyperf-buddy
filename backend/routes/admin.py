"""Admin endpoints for Cyperf sync status and manual triggering."""

import logging
import os
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from db.cverf_cve_strike_mappings import CvrfCveStrikeMappings
from db.sync_metadata import SyncMetadata
from db.system_config import SystemConfig
from dependencies import get_redis
from models import EndpointConfigRequest, EndpointConfigResponse, SyncStatusResponse
from scheduler import trigger_cyperf_sync_now
from services.cyperf_service import validate_endpoint_connectivity
from services.sync_service import perform_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Redis cache key for the CyPerf endpoint value
_CYPERF_ENDPOINT_CACHE_KEY = "cyperf:endpoint"
# TTL: 1 hour — long-lived config value changes rarely
_ENDPOINT_CACHE_TTL_SECONDS = 3600


@router.get("/config/cyperf-endpoint")
async def get_cyperf_endpoint(
    session: AsyncSession = Depends(get_db),
) -> EndpointConfigResponse:
    """Get the current Keysight CyPerf Controller endpoint configuration.

    Resolution priority:
    1. Redis cache key ``cyperf:endpoint`` (TTL = 1 hour)
    2. ``system_config`` table, config_key = ``cyperf_endpoint``
    3. Environment variable ``CYPERF_CONTROLLER_IP``
    4. Empty string (degraded response — no configuration found)

    If a database value is found and cache is unavailable, the endpoint is returned
    directly from the database without populating cache (graceful degradation).

    Returns:
        EndpointConfigResponse — always HTTP 200, even if degraded.
    """
    # Attempt cache lookup first (optional — skip on Redis failure)
    cache: aioredis.Redis | None = None
    try:
        cache = await get_redis()
        cached_endpoint = await cache.get(_CYPERF_ENDPOINT_CACHE_KEY)
        if cached_endpoint:
            logger.debug("CyPerf endpoint served from Redis cache")
            return EndpointConfigResponse(endpoint=cached_endpoint, is_valid=True)
    except Exception as redis_exc:
        logger.warning("Redis unavailable for endpoint GET — skipping cache: %s", redis_exc)
        cache = None

    # Database lookup
    endpoint: str = ""
    try:
        db_value = await SystemConfig.get_value(session, "cyperf_endpoint")
        if db_value:
            endpoint = db_value
            logger.debug("CyPerf endpoint retrieved from database: %s", endpoint)

            # Populate cache for subsequent requests (best-effort)
            if cache is not None:
                try:
                    await cache.set(
                        _CYPERF_ENDPOINT_CACHE_KEY, endpoint, ex=_ENDPOINT_CACHE_TTL_SECONDS
                    )
                except Exception as cache_set_exc:
                    logger.warning(
                        "Failed to populate Redis cache after DB lookup: %s", cache_set_exc
                    )

    except Exception as db_exc:
        logger.error("Database unavailable for CyPerf endpoint GET: %s", db_exc)

    # Fallback: environment variable (backwards compatibility)
    if not endpoint:
        env_value = os.getenv("CYPERF_CONTROLLER_IP", "")
        if env_value:
            endpoint = env_value
            logger.info("CyPerf endpoint served from CYPERF_CONTROLLER_IP env var: %s", endpoint)

    if not endpoint:
        logger.warning("No CyPerf endpoint configured (database empty, env var not set)")

    return EndpointConfigResponse(
        endpoint=endpoint,
        is_valid=False,  # Validation status unknown for GET — POST validates and sets True
        last_validated_at=None,
        error_message=None,
    )


@router.post("/config/cyperf-endpoint")
async def set_cyperf_endpoint(
    request: EndpointConfigRequest,
    session: AsyncSession = Depends(get_db),
) -> EndpointConfigResponse:
    """Update the Keysight CyPerf Controller endpoint and validate connectivity.

    **Validation is performed before persisting.**  The endpoint is checked via
    ``validate_endpoint_connectivity`` (HTTP GET, 5-second timeout, SSL not verified
    because CyPerf ships with a self-signed certificate).  If validation fails the
    value is NOT saved and HTTP 400 is returned with the failure reason.

    On success:
    - Upserts ``config_key="cyperf_endpoint"`` in the ``system_config`` table.
    - Invalidates the Redis cache key ``cyperf:endpoint``.
    - Re-populates cache with the new value (TTL = 1 hour).
    - Returns ``EndpointConfigResponse(is_valid=True, last_validated_at=<now>)``.

    Args:
        request: ``EndpointConfigRequest`` — Pydantic-validated endpoint string.

    Returns:
        ``EndpointConfigResponse`` with ``is_valid=True`` on success.

    Raises:
        HTTPException 400: Connectivity validation failed (details in response).
        HTTPException 500: Database write failed after validation passed.
    """
    endpoint = request.endpoint

    # Step 1: Validate connectivity (never persists on failure)
    is_valid, error_message = await validate_endpoint_connectivity(endpoint)

    if not is_valid:
        logger.warning("CyPerf endpoint validation failed for %s: %s", endpoint, error_message)
        raise HTTPException(
            status_code=400,
            detail=error_message or f"Cannot reach CyPerf endpoint '{endpoint}'",
        )

    # Step 2: Persist to database (atomic upsert)
    try:
        await SystemConfig.set_value(session, "cyperf_endpoint", endpoint)
        await session.commit()
        logger.info("CyPerf endpoint saved to database: %s", endpoint)
    except Exception as db_exc:
        logger.error("Database write failed after endpoint validation passed: %s", db_exc)
        raise HTTPException(
            status_code=500,
            detail="Endpoint validated successfully but database write failed. Please retry.",
        ) from db_exc

    # Step 3: Update Redis cache (best-effort — do NOT fail if Redis is down)
    try:
        cache = await get_redis()
        # Invalidate stale value before setting new one
        await cache.delete(_CYPERF_ENDPOINT_CACHE_KEY)
        await cache.set(_CYPERF_ENDPOINT_CACHE_KEY, endpoint, ex=_ENDPOINT_CACHE_TTL_SECONDS)
        logger.debug("Redis cache updated for CyPerf endpoint: %s", endpoint)
    except Exception as redis_exc:
        # Redis being unavailable is non-fatal — DB is the source of truth
        logger.warning("Redis cache update skipped (Redis unavailable): %s", redis_exc)

    validated_at = datetime.now(tz=UTC)
    return EndpointConfigResponse(
        endpoint=endpoint,
        is_valid=True,
        last_validated_at=validated_at,
        error_message=None,
    )


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

        # Count distinct CVE IDs in cverf_cve_strike_mappings
        # Each CVE counted once regardless of how many Strikes cover it
        count_stmt = select(func.count(distinct(CvrfCveStrikeMappings.cve_id)))
        count_result = await session.execute(count_stmt)
        cves_count = count_result.scalar_one() or 0

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
        HTTPException 500: If scheduler is not running and sync execution fails

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
            from scheduler import get_scheduler

            scheduler = get_scheduler()
            trigger_cyperf_sync_now(scheduler)
            logger.info("Manual sync triggered via POST /admin/sync-cyperf (queued to scheduler)")

            return {
                "status": "sync_triggered",
                "message": "Cyperf sync queued for immediate execution",
            }

        except Exception as scheduler_error:
            # Scheduler might not be running; fall back to direct execution
            logger.warning(f"Scheduler not available ({scheduler_error}); executing sync directly")

            # Option A (fallback): Call perform_sync directly
            await perform_sync(session=session, settings=settings)

            return {
                "status": "sync_completed",
                "message": "Cyperf sync completed immediately (scheduler not running)",
            }

    except Exception as e:
        logger.error(f"Error triggering manual sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger sync: {str(e)}",
        )


@router.post("/sync-cyperf-applications")
async def sync_cyperf_applications(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger Cyperf applications and application types sync.

    Fetches all applications and application types from Cyperf Controller,
    saves them to JSON files, and ingests into the database.

    Returns:
        HTTP 202 Accepted with status message

    Note:
        This endpoint returns immediately; the actual sync happens synchronously
        before returning.
    """
    try:
        from config import get_settings
        from services.cyperf_applications_service import (
            CyperfApplicationsService,
        )

        settings = get_settings()

        # Initialize service
        service = CyperfApplicationsService(
            controller_ip=settings.cyperf_controller_ip,
            username=settings.cyperf_username,
            password=settings.cyperf_password,
        )

        # Fetch data
        logger.info("Fetching Cyperf applications and application types...")
        app_types = await service.fetch_application_types()
        apps = await service.fetch_applications()

        # Save to JSON
        logger.info("Saving to JSON files...")
        from services.cyperf_applications_service import (
            APPLICATION_TYPES_FILE,
            APPLICATIONS_FILE,
        )

        service._save_to_json(APPLICATION_TYPES_FILE, app_types)
        service._save_to_json(APPLICATIONS_FILE, apps)

        # Ingest to database
        logger.info("Ingesting into database...")
        await service.ingest_application_types(session, app_types)
        await service.ingest_applications(session, apps)

        logger.info(f"✓ Synced {len(app_types)} app types and {len(apps)} applications")

        return {
            "status": "sync_completed",
            "message": f"Synced {len(app_types)} app types and {len(apps)} applications",
            "app_types_count": len(app_types),
            "applications_count": len(apps),
        }

    except Exception as e:
        logger.error(f"Error syncing Cyperf applications: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync applications: {str(e)}",
        )
