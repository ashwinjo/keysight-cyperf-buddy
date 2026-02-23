"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import get_settings
from routes.health import router as health_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load settings at module level (triggers credential validation)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Application lifespan context manager."""
    # Startup
    logger.info("✓ Application startup complete")
    yield
    # Shutdown
    logger.info("✓ Application shutdown")


# Create FastAPI application
app = FastAPI(
    title="Cyperf CVE Tracker API",
    description="Query CVE data and Cyperf testability status",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
