"""Unit tests for GET/POST /admin/config/cyperf-endpoint endpoints.

Test strategy:
- All external calls (Redis, HTTP connectivity check) are mocked.
- Database uses in-memory SQLite via the shared db_session fixture.
- Validates: cache hit fast-path, DB lookup, env-var fallback, empty degraded response,
  validation success/failure, DB save, cache update, HTTP error codes.

Fixtures reused from conftest.py:
    test_client — AsyncClient with mocked NVD + Cache + in-memory DB
    db_session  — raw AsyncSession (in-memory SQLite) for ORM assertions

The test_client fixture wires get_db -> db_session, so both share the same session.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from db.system_config import SystemConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis_mock(cached_value: str | None = None) -> AsyncMock:
    """Build an AsyncMock Redis client that mimics get/set/delete behaviour."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = cached_value
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock


# ---------------------------------------------------------------------------
# GET /admin/config/cyperf-endpoint — cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_returns_cached_value(test_client, monkeypatch):
    """GET returns endpoint from Redis cache without hitting DB."""
    redis_mock = _make_redis_mock(cached_value="cached-cyperf.example.com")

    with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "cached-cyperf.example.com"
    assert body["is_valid"] is True


# ---------------------------------------------------------------------------
# GET /admin/config/cyperf-endpoint — DB fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_falls_back_to_db(test_client, db_session, monkeypatch):
    """GET resolves endpoint from DB when Redis cache is empty."""
    # Seed the database
    await SystemConfig.set_value(db_session, "cyperf_endpoint", "db-cyperf.example.com")
    await db_session.commit()

    redis_mock = _make_redis_mock(cached_value=None)  # cache miss

    with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "db-cyperf.example.com"
    # Cache should have been populated after DB hit
    redis_mock.set.assert_called_once()


# ---------------------------------------------------------------------------
# GET /admin/config/cyperf-endpoint — env-var fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_falls_back_to_env_var(test_client, db_session, monkeypatch):
    """GET falls back to CYPERF_CONTROLLER_IP env var when DB is also empty."""
    monkeypatch.setenv("CYPERF_CONTROLLER_IP", "env-cyperf.example.com")

    redis_mock = _make_redis_mock(cached_value=None)

    with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "env-cyperf.example.com"


# ---------------------------------------------------------------------------
# GET /admin/config/cyperf-endpoint — Redis unavailable (degraded)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_redis_unavailable_uses_db(test_client, db_session, monkeypatch):
    """GET serves DB value gracefully when Redis raises an exception."""
    await SystemConfig.set_value(db_session, "cyperf_endpoint", "no-redis-cyperf.example.com")
    await db_session.commit()

    async def _failing_redis():
        raise RuntimeError("Redis connection refused")

    with patch("routes.admin.get_redis", new=_failing_redis):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "no-redis-cyperf.example.com"


# ---------------------------------------------------------------------------
# GET /admin/config/cyperf-endpoint — empty degraded response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_returns_empty_when_no_config(test_client, monkeypatch):
    """GET returns empty endpoint with HTTP 200 when no config source has a value."""
    # Ensure env var is not set
    monkeypatch.delenv("CYPERF_CONTROLLER_IP", raising=False)

    redis_mock = _make_redis_mock(cached_value=None)

    with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "" or body["endpoint"] == os.getenv("CYPERF_CONTROLLER_IP", "")
    assert body["is_valid"] is False


# ---------------------------------------------------------------------------
# GET — response shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_endpoint_response_has_required_fields(test_client):
    """GET response always includes endpoint, is_valid, last_validated_at, error_message."""
    redis_mock = _make_redis_mock(cached_value="shape-check.example.com")

    with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
        response = await test_client.get("/admin/config/cyperf-endpoint")

    assert response.status_code == 200
    body = response.json()
    assert "endpoint" in body
    assert "is_valid" in body
    assert "last_validated_at" in body
    assert "error_message" in body


# ---------------------------------------------------------------------------
# POST /admin/config/cyperf-endpoint — success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_endpoint_validates_and_saves(test_client, db_session):
    """POST validates connectivity, saves to DB, updates cache, returns is_valid=True."""
    redis_mock = _make_redis_mock(cached_value=None)

    with (
        patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
        patch(
            "routes.admin.validate_endpoint_connectivity",
            new=AsyncMock(return_value=(True, "")),
        ),
    ):
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "cyperf.example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["endpoint"] == "cyperf.example.com"
    assert body["is_valid"] is True
    assert body["last_validated_at"] is not None
    assert body["error_message"] is None

    # Cache must be invalidated then re-populated
    redis_mock.delete.assert_called_once_with("cyperf:endpoint")
    redis_mock.set.assert_called_once()

    # DB must contain the new value
    saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
    assert saved == "cyperf.example.com"


# ---------------------------------------------------------------------------
# POST — validation failure (HTTP 400)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_endpoint_returns_400_on_connectivity_failure(test_client):
    """POST returns HTTP 400 with clear error if endpoint is unreachable."""
    redis_mock = _make_redis_mock(cached_value=None)

    with (
        patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
        patch(
            "routes.admin.validate_endpoint_connectivity",
            new=AsyncMock(
                return_value=(False, "Endpoint unreachable (connection timeout after 5 seconds)")
            ),
        ),
    ):
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "unreachable.cyperf.example.com"},
        )

    assert response.status_code == 400
    body = response.json()
    assert "timeout" in body["detail"].lower() or "unreachable" in body["detail"].lower()


# ---------------------------------------------------------------------------
# POST — Pydantic validation (HTTP 422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_endpoint_422_on_empty_endpoint(test_client):
    """POST returns 422 Unprocessable Entity when endpoint is empty string."""
    response = await test_client.post(
        "/admin/config/cyperf-endpoint",
        json={"endpoint": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_endpoint_422_on_credential_in_endpoint(test_client):
    """POST returns 422 when endpoint contains embedded credentials (@ char)."""
    response = await test_client.post(
        "/admin/config/cyperf-endpoint",
        json={"endpoint": "user:pass@cyperf.example.com"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_endpoint_strips_https_prefix(test_client, db_session):
    """POST strips https:// prefix and saves bare hostname."""
    redis_mock = _make_redis_mock(cached_value=None)

    with (
        patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
        patch(
            "routes.admin.validate_endpoint_connectivity",
            new=AsyncMock(return_value=(True, "")),
        ),
    ):
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "https://cyperf.example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    # Protocol prefix must be stripped by Pydantic validator before save
    assert body["endpoint"] == "cyperf.example.com"
    saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
    assert saved == "cyperf.example.com"


# ---------------------------------------------------------------------------
# POST — Redis unavailable does not prevent save (graceful degradation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_endpoint_succeeds_when_redis_unavailable(test_client, db_session):
    """POST saves endpoint to DB even when Redis cache update fails."""

    async def _failing_redis():
        raise RuntimeError("Redis not running")

    with (
        patch("routes.admin.get_redis", new=_failing_redis),
        patch(
            "routes.admin.validate_endpoint_connectivity",
            new=AsyncMock(return_value=(True, "")),
        ),
    ):
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "no-redis-save.example.com"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True

    saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
    assert saved == "no-redis-save.example.com"


# ---------------------------------------------------------------------------
# POST — last_validated_at is an ISO 8601 timestamp
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_endpoint_last_validated_at_is_utc_timestamp(test_client):
    """POST response last_validated_at is a parseable UTC ISO 8601 timestamp."""
    redis_mock = _make_redis_mock(cached_value=None)

    with (
        patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
        patch(
            "routes.admin.validate_endpoint_connectivity",
            new=AsyncMock(return_value=(True, "")),
        ),
    ):
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "timestamp-check.example.com"},
        )

    assert response.status_code == 200
    ts_str = response.json()["last_validated_at"]
    assert ts_str is not None
    # Must be parseable as a datetime
    parsed = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None  # must be timezone-aware


# ---------------------------------------------------------------------------
# SystemConfig ORM model — unit tests independent of HTTP layer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_system_config_get_value_returns_none_for_missing_key(db_session):
    """get_value returns None by default for a key that does not exist."""
    result = await SystemConfig.get_value(db_session, "nonexistent_key")
    assert result is None


@pytest.mark.asyncio
async def test_system_config_get_value_returns_default_for_missing_key(db_session):
    """get_value returns provided default for a key that does not exist."""
    result = await SystemConfig.get_value(db_session, "nonexistent_key", default="fallback")
    assert result == "fallback"


@pytest.mark.asyncio
async def test_system_config_set_value_creates_new_entry(db_session):
    """set_value creates a new row when key does not exist."""
    await SystemConfig.set_value(db_session, "test_key", "test_value")
    await db_session.commit()

    result = await SystemConfig.get_value(db_session, "test_key")
    assert result == "test_value"


@pytest.mark.asyncio
async def test_system_config_set_value_updates_existing_entry(db_session):
    """set_value updates existing value when key already exists (upsert)."""
    await SystemConfig.set_value(db_session, "upsert_key", "original")
    await db_session.commit()

    await SystemConfig.set_value(db_session, "upsert_key", "updated")
    await db_session.commit()

    result = await SystemConfig.get_value(db_session, "upsert_key")
    assert result == "updated"
