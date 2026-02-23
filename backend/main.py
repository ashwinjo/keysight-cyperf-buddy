"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from routes.admin import router as admin_router
from routes.cve import router as cve_router
from routes.health import router as health_router
from scheduler import set_scheduler, setup_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load settings at module level (triggers credential validation)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Application lifespan context manager.

    Manages startup and shutdown of background services:
    - APScheduler for Cyperf sync jobs
    - Database connections
    """
    # Startup
    scheduler = None

    try:
        logger.info("✓ Application startup")

        # Initialize and start Cyperf sync scheduler
        scheduler = setup_scheduler(app, settings)
        scheduler.start()
        set_scheduler(scheduler)
        logger.info("✓ Cyperf sync scheduler started (02:00 UTC, ±5min jitter)")

    except Exception as e:
        logger.error(f"Scheduler startup failed: {e}; app continues with manual sync only")

    yield

    # Shutdown
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("✓ Scheduler shutdown complete")
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {e}")

    logger.info("✓ Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Cyperf CVE Tracker API",
    description="Query CVE data and Cyperf testability status",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)
app.include_router(cve_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
