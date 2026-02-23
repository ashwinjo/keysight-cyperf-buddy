"""Redis CVE cache service.

Key scheme:  cve:v1:{CVE_ID_UPPERCASE}
TTL:         86400s base +/- 3600s jitter (23h-25h window)
Serialization: JSON with default=str

All public methods catch Redis exceptions and return None/False on failure.
Redis unavailability must NOT propagate as an API error.
"""

import json
import logging
import random

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# TTL constants
CVE_CACHE_TTL_SECONDS = 86400  # 24 hours base
CVE_CACHE_TTL_JITTER_SECONDS = 3600  # +/- 1 hour jitter

# SWR threshold: refresh if remaining TTL falls below this value
STALE_REFRESH_THRESHOLD_SECONDS = 4 * 3600  # 4 hours


def _make_cache_key(cve_id: str) -> str:
    """Canonical Redis key for a CVE record. Always uppercase-normalized."""
    return f"cve:v1:{cve_id.upper()}"


def _ttl_with_jitter() -> int:
    """Returns TTL between 23h and 25h to spread cache expiry."""
    return CVE_CACHE_TTL_SECONDS + random.randint(
        -CVE_CACHE_TTL_JITTER_SECONDS, CVE_CACHE_TTL_JITTER_SECONDS
    )


class CVECacheService:
    """Cache-aside service for CVE records backed by Redis."""

    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def get(self, cve_id: str) -> dict | None:
        """Return cached CVE dict or None on cache miss or Redis failure.

        Never raises — Redis failure returns None (cache miss).
        """
        key = _make_cache_key(cve_id)
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis GET failed for %s: %s", key, exc)
            return None

    async def set(self, cve_id: str, data: dict) -> bool:
        """Store CVE dict in Redis with TTL jitter.

        Returns True on success, False on Redis failure.
        """
        key = _make_cache_key(cve_id)
        try:
            serialized = json.dumps(data, default=str)
            ttl = _ttl_with_jitter()
            await self._redis.set(key, serialized, ex=ttl)
            logger.debug("Cached CVE %s with TTL=%ds", cve_id, ttl)
            return True
        except Exception as exc:
            logger.warning("Redis SET failed for %s: %s", key, exc)
            return False

    async def get_remaining_ttl(self, cve_id: str) -> int:
        """Return remaining TTL in seconds.

        Returns -2 if key does not exist, -1 if no TTL set.
        Returns 0 on Redis failure (treat as stale).
        """
        key = _make_cache_key(cve_id)
        try:
            return await self._redis.ttl(key)
        except Exception as exc:
            logger.warning("Redis TTL check failed for %s: %s", key, exc)
            return 0  # Treat failure as stale -> triggers refresh attempt

    async def exists(self, cve_id: str) -> bool:
        """Check if CVE is in cache. Returns False on Redis failure."""
        key = _make_cache_key(cve_id)
        try:
            return bool(await self._redis.exists(key))
        except Exception as exc:
            logger.warning("Redis EXISTS failed for %s: %s", key, exc)
            return False

    def is_stale(self, remaining_ttl: int) -> bool:
        """True if remaining TTL indicates the entry should be proactively refreshed.

        Triggers stale-while-revalidate background refresh.
        """
        return 0 <= remaining_ttl < STALE_REFRESH_THRESHOLD_SECONDS
