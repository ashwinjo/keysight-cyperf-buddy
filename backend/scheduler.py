"""APScheduler initialization and job setup for Cyperf sync."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from database import get_db_session
from services.sync_service import perform_sync

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


class SchedulerNotStartedError(Exception):
    """Raised when scheduler is not started."""

    pass


def setup_scheduler(app: FastAPI, settings: Settings) -> AsyncIOScheduler:
    """Initialize and configure APScheduler for Cyperf sync jobs.

    Sets up an AsyncIOScheduler with UTC timezone and adds a daily cron job
    for syncing Cyperf attack profiles at 02:00 UTC with ±5 minute jitter.

    Args:
        app: FastAPI application instance
        settings: Application settings with Cyperf credentials and sync interval

    Returns:
        Configured AsyncIOScheduler instance (not yet started)

    Note:
        The scheduler is returned but not started here; starting happens in
        the FastAPI lifespan context manager (in main.py).
    """
    logger.info("Setting up APScheduler for Cyperf sync jobs...")

    try:
        # Initialize AsyncIOScheduler with UTC timezone
        scheduler = AsyncIOScheduler(timezone="UTC")
        logger.info("✓ AsyncIOScheduler initialized with UTC timezone")

        # Add the daily Cyperf sync job
        # Runs at 02:00 UTC daily with ±5 minute random jitter
        # If job is delayed, it will still run if within 10 minutes of scheduled time
        scheduler.add_job(
            sync_cyperf_job,
            trigger=CronTrigger(hour=2, minute=0, timezone="UTC", jitter=300),
            args=[app, settings],
            id="cyperf_sync",
            name="Cyperf Attack Profile Sync",
            misfire_grace_time=600,
            coalesce=True,  # Don't run multiple times if delayed
            max_instances=1,  # Only one instance at a time
            replace_existing=True,
        )
        logger.info(
            "✓ Added daily cron job: 02:00 UTC daily with ±5min jitter, misfire grace 10min"
        )

        return scheduler

    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        raise


async def sync_cyperf_job(app: FastAPI, settings: Settings) -> None:
    """Background job function for syncing Cyperf profiles.

    This function is called on schedule by APScheduler. It orchestrates the
    complete sync cycle:
    1. Creates database session
    2. Calls perform_sync() for full sync with retry and graceful degradation
    3. Records results in sync_metadata
    4. Closes session

    Args:
        app: FastAPI application instance
        settings: Application settings

    Note:
        Error handling is comprehensive: all Cyperf and database errors are
        caught and recorded gracefully. The job never raises exceptions.
    """
    start_time = datetime.utcnow()
    logger.info("✓ Cyperf sync job started (scheduled: 02:00 UTC, ±5min jitter)")

    session: AsyncSession | None = None

    try:
        # Create database session for this sync job
        session = await get_db_session()

        # Call perform_sync with full orchestration:
        # - Retry logic (immediate + 5s delay)
        # - Graceful degradation (log failure, retain previous data)
        # - Database recording (sync_metadata)
        await perform_sync(session=session, settings=settings)

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✓ Cyperf sync job completed (duration: {duration:.2f}s)")

    except Exception as e:
        # Log error but don't re-raise; let scheduler continue
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.error(
            f"Cyperf sync job failed with exception: {type(e).__name__}: {e} (duration: {duration:.2f}s)"
        )

    finally:
        # Ensure session is closed
        if session:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")


def trigger_cyperf_sync_now(scheduler: AsyncIOScheduler | None = None) -> None:
    """Manually trigger an immediate Cyperf sync (for POST /admin/sync-cyperf).

    Adds a one-time job to the scheduler that runs immediately. This allows
    admins/developers to force a sync outside the normal 24-hour schedule.

    Args:
        scheduler: AsyncIOScheduler instance (uses global if not provided)

    Raises:
        SchedulerNotStartedError: If scheduler is not running

    Note:
        In Plan 02, this is called by the POST /admin/sync-cyperf endpoint.
    """
    sched = scheduler or _scheduler

    if not sched or not sched.running:
        logger.warning("Cannot trigger sync; scheduler not running")
        raise SchedulerNotStartedError("Scheduler is not running")

    try:
        settings = get_settings()

        # Create a minimal FastAPI-like object for sync_cyperf_job
        # In Plan 02, this is refactored to not need the app object
        class MinimalApp:
            pass

        app = MinimalApp()

        sched.add_job(
            sync_cyperf_job,
            trigger="date",
            run_date=datetime.utcnow(),
            args=[app, settings],
            id=f"manual_sync_{int(datetime.utcnow().timestamp())}",
            name="Manual Cyperf Sync",
            replace_existing=False,
        )
        logger.info("✓ Queued immediate manual Cyperf sync")

    except Exception as e:
        logger.error(f"Failed to queue manual sync: {e}")
        raise


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance.

    Returns:
        Global AsyncIOScheduler instance

    Raises:
        SchedulerNotStartedError: If scheduler has not been initialized
    """
    global _scheduler
    if _scheduler is None:
        raise SchedulerNotStartedError("Scheduler not initialized")
    return _scheduler


def set_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Set the global scheduler instance.

    Args:
        scheduler: AsyncIOScheduler to store globally
    """
    global _scheduler
    _scheduler = scheduler
