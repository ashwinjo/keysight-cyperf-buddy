"""Cyperf sync orchestration service with graceful degradation."""

import asyncio
import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from db.cyperf_mapping import CyperfSupportedCVE
from db.sync_metadata import SyncMetadata
from services.cyperf_service import CyperfAPIError, CyperfConnectionError, CyperfService

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Raised when sync operation fails unrecoverably."""

    pass


async def perform_sync(session: AsyncSession, settings: Settings) -> None:
    """Orchestrate complete Cyperf sync cycle with retry and graceful degradation.

    Handles the full sync lifecycle:
    1. Record sync attempt start
    2. Fetch profiles from Cyperf with retry logic
    3. Extract CVEs and upsert to database
    4. Record completion (success or failure)
    5. Compute next scheduled sync time

    On any Cyperf failure:
    - Retries immediately once, then after 5 second delay once more (3 total attempts)
    - Logs error details and retry count
    - Records failure in sync_metadata WITHOUT corrupting database
    - Retains ALL previous sync data (graceful degradation)
    - Does NOT re-raise exception (allows scheduler to continue)

    On database errors:
    - Rolls back transaction
    - Records failure in metadata
    - Does NOT retry (let next scheduled sync attempt recovery)

    Args:
        session: AsyncSession for database operations
        settings: Application settings (includes Cyperf credentials, sync interval)

    Raises:
        SyncError: Only raised for unexpected internal errors (not for Cyperf/DB failures)

    Note:
        This function catches all errors and records them in sync_metadata.
        It never raises for Cyperf or database errors (graceful degradation).
    """
    start_time = time.time()
    attempt_count = 0
    last_error: str | None = None

    logger.info("Starting Cyperf sync operation...")

    try:
        # Record sync attempt start
        await SyncMetadata.record_sync_start(session, job_name="cyperf_profiles")
        await session.commit()

    except Exception as e:
        logger.error(f"Failed to record sync start: {e}")
        return

    # Retry logic: attempt 1 (immediate), attempt 2 (no wait), attempt 3 (5s wait)
    for attempt_number in range(1, 4):
        attempt_count = attempt_number

        if attempt_number > 1:
            if attempt_number == 3:
                # Before final retry, wait 5 seconds
                logger.info("Waiting 5 seconds before final retry...")
                await asyncio.sleep(5)
            else:
                logger.info("Retrying immediately...")

        try:
            logger.info(f"Cyperf sync attempt {attempt_number}/3...")

            # Initialize Cyperf service
            cyperf_service = CyperfService(
                controller_ip=settings.cyperf_controller_ip,
                username=settings.cyperf_username,
                password=settings.cyperf_password,
            )

            # Fetch profiles and extract CVEs
            result = await cyperf_service.sync_cyperf_cves()

            if result.error:
                # CVE extraction had errors but may have partial results
                last_error = result.error
                logger.warning(f"Sync had errors: {result.error}")

                # Even with errors, if we got some data, record it
                if result.cves_extracted == 0:
                    # No data retrieved; this counts as failure
                    logger.error(f"No CVEs extracted; attempt {attempt_number} failed")
                    if attempt_number == 3:
                        # All retries failed
                        break
                    continue

            # Sync succeeded; upsert CVE mappings to database
            try:
                # Get CVE mappings from service
                # Note: cyperf_service.extract_cves_from_profiles returns Dict[cve_id, profile_name]
                # We need to fetch profiles again to have the mapping data
                profiles = await cyperf_service.fetch_attack_profiles()
                cve_mappings = cyperf_service.extract_cves_from_profiles(profiles)

                # Upsert each CVE-profile mapping atomically
                for cve_id, profile_name in cve_mappings.items():
                    CyperfSupportedCVE.upsert_from_cyperf_data(
                        session=session,
                        cve_id=cve_id,
                        profile_name=profile_name,
                    )

                # Commit all upserts in a single transaction
                await session.commit()

                logger.info(f"✓ Upserted {len(cve_mappings)} CVE-profile mappings to database")

                # Record successful completion
                await SyncMetadata.record_sync_complete(
                    session=session,
                    job_name="cyperf_profiles",
                    success=True,
                    profiles_count=result.profiles_fetched,
                    cves_count=result.cves_extracted,
                    error_msg=None,
                    next_sync_hours=settings.cyperf_sync_interval_hours,
                )
                await session.commit()

                duration = time.time() - start_time
                logger.info(
                    f"✓ Cyperf sync SUCCEEDED: {result.profiles_fetched} profiles, "
                    f"{result.cves_extracted} CVEs, {duration:.2f}s, attempt {attempt_number}"
                )

                # Check for circuit breaker condition (consecutive failures)
                consecutive_failures = await SyncMetadata.get_consecutive_failures(session)
                if consecutive_failures > 0:
                    # Previous syncs had failed; reset on success
                    logger.info(f"Circuit breaker: resetting after {consecutive_failures} failures")

                return  # Success; exit retry loop

            except Exception as db_error:
                # Database operation failed
                await session.rollback()
                logger.error(f"Database error during upsert: {db_error}")
                last_error = f"Database write failed: {str(db_error)}"

                if attempt_number == 3:
                    # All retries failed; record failure and exit
                    break
                # Otherwise retry with next attempt

        except (CyperfConnectionError, CyperfAPIError) as e:
            # Cyperf error; log and retry
            logger.warning(f"Cyperf error on attempt {attempt_number}: {e}")
            last_error = f"Cyperf error: {str(e)}"

            if attempt_number == 3:
                # All retries failed; exit retry loop
                break
            # Otherwise continue to next retry

        except Exception as e:
            # Unexpected error; log and treat as Cyperf failure for retry
            logger.error(f"Unexpected error on attempt {attempt_number}: {type(e).__name__}: {e}")
            last_error = f"Unexpected error: {str(e)}"

            if attempt_number == 3:
                break

    # All retries failed; record failure and check circuit breaker
    try:
        duration = time.time() - start_time
        logger.error(
            f"Cyperf sync FAILED after {attempt_count} attempts: {last_error} "
            f"(duration: {duration:.2f}s); retaining previous sync data"
        )

        # Record sync failure
        await SyncMetadata.record_sync_complete(
            session=session,
            job_name="cyperf_profiles",
            success=False,
            profiles_count=0,
            cves_count=0,
            error_msg=last_error,
            next_sync_hours=settings.cyperf_sync_interval_hours,
        )
        await session.commit()

        # Check consecutive failures for circuit breaker alert
        consecutive_failures = await SyncMetadata.get_consecutive_failures(session)
        if consecutive_failures >= 3:
            logger.error(
                "Circuit breaker: 3 consecutive sync failures. Check Cyperf controller availability."
            )

    except Exception as e:
        logger.error(f"Failed to record sync failure: {e}")


async def get_sync_status(session: AsyncSession) -> SyncMetadata | None:
    """Retrieve current sync status metadata.

    Args:
        session: AsyncSession for database queries
        job_name: Name of sync job (default: 'cyperf_profiles')

    Returns:
        SyncMetadata record or None if never synced
    """
    return await SyncMetadata.get_last_sync_status(session, job_name="cyperf_profiles")
