"""Admin endpoints for Cyperf sync status and manual triggering."""

import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

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
from scheduler import get_scheduler
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


@router.post("/sync-all")
async def sync_all(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger a full sync: apps + app types (synchronous) then CVE profiles (queued).

    Execution order:
    1. Validate endpoint is configured.
    2. Run ``sync-cyperf-applications`` synchronously — returns counts immediately.
    3. Queue CVE sync via APScheduler (same mechanism as ``sync-cyperf-now``).

    Returns a single response with apps counts already populated and a job_id
    for the in-flight CVE sync.  The caller should poll ``GET /admin/sync-status``
    to confirm CVE sync completion.

    Returns:
        HTTP 200 with ``status="sync_queued"``, ``job_id``, and ``apps_synced`` counts.
        HTTP 400 if endpoint is not configured.
        HTTP 500 if both apps sync and CVE queue fail.
    """
    # Validate endpoint
    endpoint: str = ""
    try:
        config_value = await SystemConfig.get_value(session, "cyperf_endpoint")
        if config_value and config_value.strip():
            endpoint = config_value.strip()
    except Exception as db_exc:
        logger.warning("DB read failed during sync-all endpoint check: %s", db_exc)

    if not endpoint:
        env_endpoint = os.getenv("CYPERF_CONTROLLER_IP", "").strip()
        if not env_endpoint:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cyperf endpoint not configured. "
                    "Visit settings to configure the endpoint before syncing."
                ),
            )
        endpoint = env_endpoint

    # Step 1: Apps sync (synchronous — fast, completes before returning)
    # Use a fresh session to avoid transaction conflicts with the request session.
    apps_synced: dict = {"app_types_count": 0, "applications_count": 0}
    try:
        from database import get_db_session
        from services.cyperf_applications_service import (
            APPLICATION_TYPES_FILE,
            APPLICATIONS_FILE,
            CyperfApplicationsService,
        )

        settings = get_settings()
        service = CyperfApplicationsService(
            controller_ip=settings.cyperf_controller_ip or endpoint,
            username=settings.cyperf_username,
            password=settings.cyperf_password,
        )
        app_types = await service.fetch_application_types()
        apps = await service.fetch_applications()
        service._save_to_json(APPLICATION_TYPES_FILE, app_types)
        service._save_to_json(APPLICATIONS_FILE, apps)
        apps_session = await get_db_session()
        try:
            await service.ingest_application_types(apps_session, app_types)
            await service.ingest_applications(apps_session, apps)
        finally:
            await apps_session.close()
        apps_synced = {
            "app_types_count": len(app_types),
            "applications_count": len(apps),
        }
        logger.info(
            "sync-all: apps sync completed (%d types, %d apps)",
            len(app_types),
            len(apps),
        )
    except Exception as apps_exc:
        # Non-fatal: log and continue to CVE sync
        logger.error("sync-all: apps sync failed (continuing to CVE sync): %s", apps_exc)
        apps_synced["error"] = str(apps_exc)

    # Step 2: CVE sync (queued via APScheduler)
    settings = get_settings()
    try:
        from scheduler import sync_cyperf_job

        scheduler = get_scheduler()
        if not scheduler.running:
            raise RuntimeError("Scheduler is initialized but not running")

        job_id = f"manual_sync_{uuid4()}"

        class _MinimalApp:
            pass

        job = scheduler.add_job(
            sync_cyperf_job,
            trigger="date",
            run_date=datetime.utcnow(),
            args=[_MinimalApp(), settings],
            id=job_id,
            name="Manual Cyperf Sync (sync-all)",
            replace_existing=False,
        )
        logger.info("sync-all: CVE sync queued (job_id=%s, endpoint=%s)", job.id, endpoint)
        return {
            "status": "sync_queued",
            "message": "Apps synced; CVE sync queued for immediate execution",
            "job_id": job.id,
            "endpoint": endpoint,
            "apps_synced": apps_synced,
        }

    except Exception as scheduler_exc:
        logger.warning(
            "sync-all: Scheduler unavailable (%s); executing CVE sync directly",
            scheduler_exc,
        )
        try:
            await perform_sync(session=session, settings=settings)
            return {
                "status": "sync_completed",
                "message": "Apps and CVE sync completed immediately (scheduler not available)",
                "job_id": None,
                "endpoint": endpoint,
                "apps_synced": apps_synced,
            }
        except Exception as sync_exc:
            logger.error("sync-all: Direct CVE sync execution failed: %s", sync_exc)
            raise HTTPException(
                status_code=500,
                detail=f"Apps sync done; CVE sync failed: {sync_exc}",
            ) from sync_exc
