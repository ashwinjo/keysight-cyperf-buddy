"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI

from config import get_settings
from dependencies import set_redis_client
from routes.admin import router as admin_router
from routes.cve import router as cve_router
from routes.health import router as health_router
from scheduler import set_scheduler, setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Application lifespan: initialize and teardown shared resources."""
    redis_client: aioredis.Redis | None = None

    # Initialize Redis connection pool
    try:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await redis_client.ping()
        set_redis_client(redis_client)
        logger.info("Redis connection pool initialized: %s", settings.redis_url)
    except Exception as exc:
        logger.warning(
            "Redis unavailable at startup: %s. Cache will be bypassed until Redis recovers.",
            exc,
        )

    # NVD API key presence check (non-fatal — rate limits apply without key)
    if settings.nvd_api_key:
        logger.info("NVD API key configured (100 req/min limit)")
    else:
        logger.warning(
            "NVD_API_KEY not set — operating at 10 req/min NVD limit. "
            "Set NVD_API_KEY in environment for production use."
        )

    # Initialize and start Cyperf sync scheduler
    scheduler = None
    try:
        scheduler = setup_scheduler(app, settings)
        scheduler.start()
        set_scheduler(scheduler)
        logger.info("Cyperf sync scheduler started (02:00 UTC, +/-5min jitter)")

        # Trigger immediate sync on startup to populate CVE database
        try:
            from datetime import datetime

            from scheduler import sync_cyperf_job

            scheduler.add_job(
                sync_cyperf_job,
                trigger="date",
                run_date=datetime.utcnow(),
                args=[app, settings],
                id="startup_sync",
                name="Startup Cyperf Sync",
                replace_existing=False,
            )
            logger.info("✓ Queued immediate startup Cyperf sync")
        except Exception as exc:
            logger.error("Failed to queue startup sync: %s; will use scheduled sync instead", exc)

    except Exception as exc:
        logger.error("Scheduler startup failed: %s; app continues with manual sync only", exc)

    logger.info("Application startup complete")
    yield

    # Shutdown: stop scheduler
    try:
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown complete")
    except Exception as exc:
        logger.error("Scheduler shutdown error: %s", exc)

    # Shutdown: close Redis connection pool
    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection pool closed")

    logger.info("Application shutdown complete")


app = FastAPI(
    title="Cyperf CVE Tracker API",
    description="Query CVE data and Cyperf testability status",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(cve_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
