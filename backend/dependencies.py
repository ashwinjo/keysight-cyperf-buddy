"""Shared FastAPI dependency providers.

All application-level singletons are declared here and injected via Depends().
This keeps lifespan management in main.py and dependency resolution in one place.
"""

from functools import lru_cache

import redis.asyncio as aioredis
from fastapi import Depends

from config import get_settings
from services.cache_service import CVECacheService
from services.nvd_service import NVDClient

# ---------------------------------------------------------------------------
# NVD Client — singleton initialized at first call
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_nvd_client() -> NVDClient:
    """Singleton NVDClient — shared across all requests."""
    return NVDClient(api_key=get_settings().nvd_api_key)


# ---------------------------------------------------------------------------
# Redis Client — module-level singleton, injected from main.py lifespan
# ---------------------------------------------------------------------------

_redis_client: aioredis.Redis | None = None


def set_redis_client(client: aioredis.Redis) -> None:
    """Called from main.py lifespan on startup to inject the live Redis client."""
    global _redis_client
    _redis_client = client


async def get_redis() -> aioredis.Redis:
    """FastAPI dependency: shared Redis client.

    Raises RuntimeError if called before lifespan startup.
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized — lifespan not run")
    return _redis_client


async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis),
) -> CVECacheService:
    """FastAPI dependency: CVECacheService bound to shared Redis client."""
    return CVECacheService(redis)
