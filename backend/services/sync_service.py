"""Cyperf sync orchestration service with graceful degradation."""

import asyncio
import json
import logging
import os
import time

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from db.ai_cves import AICve
from db.cverf_cve_strike_mappings import CvrfCveStrikeMappings
from db.sync_metadata import SyncMetadata
from services.cyperf_service import (
    AIStrikeRecord,
    CyperfAPIError,
    CyperfConnectionError,
    CyperfService,
    StrikeFetchResult,
)

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Raised when sync operation fails unrecoverably."""

    pass


async def perform_sync(session: AsyncSession, settings: Settings) -> None:
    """Orchestrate complete Cyperf sync cycle with retry and graceful degradation.

    Handles the full sync lifecycle:
    1. Record sync attempt start
    2. Fetch CVE→Strike mappings from Cyperf with retry logic
    3. Atomic full-replace: delete all existing cverf_cve_strike_mappings, insert fresh
    4. Write JSON artifact to ./data/cve_strikes.json
    5. Record completion (success or failure)

    On any Cyperf failure:
    - Retries immediately once, then after 5 second delay once more (3 total attempts)
    - Logs error details and retry count
    - Records failure in sync_metadata WITHOUT corrupting database
    - Retains ALL previous cverf_cve_strike_mappings rows (graceful degradation)
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

            # Fetch all CVE→Strike mappings and AI-type strikes (paginated, batched)
            fetch_result: StrikeFetchResult = await cyperf_service.fetch_cve_strike_mappings()
            cve_mappings = fetch_result.cve_mappings
            ai_strikes: list[AIStrikeRecord] = fetch_result.ai_strikes
            cves_count = len(cve_mappings)

            if cves_count == 0:
                logger.warning(f"Sync returned 0 CVE mappings on attempt {attempt_number}")
                last_error = "No CVE mappings returned from Cyperf"
                if attempt_number == 3:
                    break
                continue

            # Atomic full-replace: delete all existing rows from both tables,
            # then insert fresh data. Both tables are updated in a single
            # transaction — if either insert fails, both roll back.
            try:
                async with session.begin():
                    await session.execute(delete(CvrfCveStrikeMappings))
                    for cve_id, strike_name in cve_mappings.items():
                        session.add(CvrfCveStrikeMappings(cve_id=cve_id, strike_name=strike_name))

                    # Full-replace AI strikes in the same transaction
                    await session.execute(delete(AICve))
                    for record in ai_strikes:
                        session.add(
                            AICve(
                                id=record.row_id,
                                cve_id=record.cve_id,
                                strike_name=record.strike_name,
                                strike_type=record.strike_type,
                                metadata=record.metadata_json,
                            )
                        )

                logger.info(f"Full-replace sync: inserted {cves_count} CVE-Strike mappings")
                logger.info(
                    f"Full-replace sync: inserted {len(ai_strikes)} AI strike rows into ai_cves"
                )

                # Write JSON artifact (outside transaction — non-fatal if write fails)
                try:
                    output_path = (
                        getattr(settings, "cve_strikes_output_path", None)
                        or "./data/cve_strikes.json"
                    )
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "w") as f:
                        json.dump(cve_mappings, f, indent=2)
                    logger.info(f"Wrote CVE-Strike JSON artifact to {output_path}")
                except Exception as json_err:
                    logger.warning(
                        f"Failed to write CVE-Strike JSON artifact: {json_err} (sync continues)"
                    )

                # Record successful completion
                # profiles_count not tracked separately; pass cves_count as proxy
                await SyncMetadata.record_sync_complete(
                    session=session,
                    job_name="cyperf_profiles",
                    success=True,
                    profiles_count=cves_count,
                    cves_count=cves_count,
                    error_msg=None,
                    next_sync_hours=settings.cyperf_sync_interval_hours,
                )
                await session.commit()

                # Check for circuit breaker condition (consecutive failures)
                consecutive_failures = await SyncMetadata.get_consecutive_failures(session)
                if consecutive_failures > 0:
                    logger.info(f"Circuit breaker: resetting after {consecutive_failures} failures")

                duration = time.time() - start_time
                logger.info(
                    f"Cyperf sync SUCCEEDED: {cves_count} CVE mappings, "
                    f"{duration:.2f}s, attempt {attempt_number}"
                )
                return  # Success; exit retry loop

            except Exception as db_error:
                await session.rollback()
                logger.error(f"Database error during full-replace: {db_error}")
                last_error = f"Database write failed: {str(db_error)}"
                if attempt_number == 3:
                    break

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
                "Circuit breaker: 3 consecutive sync failures. "
                "Check Cyperf controller availability."
            )

    except Exception as e:
        logger.error(f"Failed to record sync failure: {e}")


async def get_sync_status(session: AsyncSession) -> SyncMetadata | None:
    """Retrieve current sync status metadata.

    Args:
        session: AsyncSession for database queries

    Returns:
        SyncMetadata record or None if never synced
    """
    return await SyncMetadata.get_last_sync_status(session, job_name="cyperf_profiles")
