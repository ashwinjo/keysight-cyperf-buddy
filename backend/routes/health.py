"""Health check endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from services.health_service import check_database, check_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> dict:
    """Basic liveness check."""
    return {"status": "ok"}


@router.get("/redis")
async def redis_health() -> dict:
    """Check Redis connectivity."""
    settings = get_settings()
    result = await check_redis(settings.redis_url)
    if result["status"] != "ok":
        raise HTTPException(status_code=503, detail=result)
    return result


@router.get("/db")
async def db_health(db: AsyncSession = Depends(get_db)) -> dict:
    """Check database connectivity."""
    result = await check_database(db)
    if result["status"] != "ok":
        raise HTTPException(status_code=503, detail=result)
    return result
