"""Health check business logic."""

from typing import Any

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_redis(redis_url: str) -> dict[str, Any]:
    """Verify Redis connectivity.

    Args:
        redis_url: Redis connection URL.

    Returns:
        Dictionary with status and service name.
    """
    try:
        r = redis.from_url(redis_url, decode_responses=True)
        await r.ping()
        await r.close()
        return {"status": "ok", "service": "redis"}
    except Exception as e:
        return {"status": "error", "service": "redis", "error": str(e)}


async def check_database(db: AsyncSession) -> dict[str, Any]:
    """Verify database connectivity.

    Args:
        db: Database session.

    Returns:
        Dictionary with status and service name.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "database"}
    except Exception as e:
        return {"status": "error", "service": "database", "error": str(e)}
