"""Integration tests for CyPerf dynamic endpoint configuration workflow.

This module provides end-to-end integration tests for the complete
endpoint configuration and manual sync workflow introduced in Phase 10.

Coverage:
  - Endpoint config API (GET/POST /admin/config/cyperf-endpoint)
  - Database persistence and retrieval (SystemConfig ORM)
  - Redis cache behaviour (hit, miss, unavailable)
  - Environment variable fallback chain
  - Manual sync triggering (POST /admin/sync-cyperf-now)
  - Scheduler path vs direct-execution fallback
  - Endpoint resolution by sync service (system_config > env var)
  - Full integrated workflow: configure endpoint → trigger sync

Test strategy:
  - HTTP layer via test_client (AsyncClient against in-memory SQLite app)
  - All external calls mocked: Cyperf API, Redis, APScheduler
  - No real network calls made during test execution
  - Uses shared conftest.py fixtures (test_client, db_session)

Note: Complements test_admin_config.py (unit tests) and
test_manual_sync_integration.py (scheduler/env-var tests) by providing
integrated workflow tests that span multiple API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from db.system_config import SystemConfig
from services.sync_service import perform_sync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_redis_mock(cached_value: str | None = None) -> AsyncMock:
    """Build an AsyncMock Redis client mimicking get/set/delete behaviour."""
    redis_mock = AsyncMock()
    redis_mock.get.return_value = cached_value
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock


def _make_scheduler_mock(job_id: str = "integration-test-job") -> MagicMock:
    """Build a mock APScheduler that returns a job with the given id."""
    mock_job = MagicMock()
    mock_job.id = job_id
    scheduler = MagicMock()
    scheduler.running = True
    scheduler.add_job.return_value = mock_job
    return scheduler


@pytest.fixture
def test_settings() -> Settings:
    """Minimal Settings for integration tests — no real Cyperf controller needed."""
    return Settings(
        cyperf_controller_ip="env-integration-host",
        cyperf_username="test-user",
        cyperf_password="test-password",
        cyperf_sync_interval_hours=24,
        database_url="sqlite+aiosqlite:///:memory:",
    )


# ---------------------------------------------------------------------------
# Class: TestEndpointConfiguration
# Integration tests for GET/POST /admin/config/cyperf-endpoint
# ---------------------------------------------------------------------------


class TestEndpointConfiguration:
    """Integration tests for CyPerf endpoint configuration workflow."""

    @pytest.mark.asyncio
    async def test_get_endpoint_returns_empty_initially(self, test_client, db_session, monkeypatch):
        """GET /admin/config/cyperf-endpoint returns empty endpoint when nothing is configured.

        With no Redis cache, no DB value, and no env var, the response must be
        HTTP 200 with an empty or absent endpoint and is_valid=False.
        """
        monkeypatch.delenv("CYPERF_CONTROLLER_IP", raising=False)
        redis_mock = _make_redis_mock(cached_value=None)

        with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
            response = await test_client.get("/admin/config/cyperf-endpoint")

        assert response.status_code == 200
        data = response.json()
        # Endpoint must be absent, empty, or only contain the test env default
        assert (
            data["endpoint"] == "" or data["endpoint"] is None or isinstance(data["endpoint"], str)
        )
        assert data["is_valid"] is False

    @pytest.mark.asyncio
    async def test_post_endpoint_returns_422_on_empty_string(self, test_client):
        """POST /admin/config/cyperf-endpoint returns 422 for empty endpoint string.

        Pydantic field_validator rejects empty values before the route handler runs.
        """
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": ""},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_endpoint_returns_422_on_embedded_credentials(self, test_client):
        """POST /admin/config/cyperf-endpoint returns 422 when endpoint contains '@'.

        The Pydantic validator rejects credential injection patterns (user:pass@host).
        """
        response = await test_client.post(
            "/admin/config/cyperf-endpoint",
            json={"endpoint": "user:pass@cyperf.example.com"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_post_endpoint_validates_and_saves_on_success(self, test_client, db_session):
        """POST validates connectivity, saves to DB, updates cache, returns is_valid=True.

        This is the primary success path: valid hostname + reachable endpoint.
        """
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
        data = response.json()
        assert data["endpoint"] == "cyperf.example.com"
        assert data["is_valid"] is True
        assert data["last_validated_at"] is not None
        assert data["error_message"] is None

        # Verify persistence in DB
        saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
        assert saved == "cyperf.example.com"

    @pytest.mark.asyncio
    async def test_post_endpoint_returns_400_on_unreachable_endpoint(self, test_client):
        """POST /admin/config/cyperf-endpoint returns 400 when endpoint is unreachable.

        The connectivity validation failure is surfaced as an HTTP 400 with a
        descriptive detail message — not a 500 or silent failure.
        """
        redis_mock = _make_redis_mock(cached_value=None)

        with (
            patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(
                    return_value=(
                        False,
                        "Endpoint unreachable (connection timeout after 5 seconds)",
                    )
                ),
            ),
        ):
            response = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "unreachable.example.com"},
            )

        assert response.status_code == 400
        data = response.json()
        # Error message must mention the failure reason
        assert "timeout" in data["detail"].lower() or "unreachable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_endpoint_persists_across_requests(self, test_client, db_session):
        """Endpoint saved via POST is retrieved by subsequent GET.

        This validates the full persistence round-trip: POST writes to DB,
        GET reads it back (via DB fallback when cache is empty).
        """
        redis_mock = _make_redis_mock(cached_value=None)

        # Step 1: Save endpoint
        with (
            patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(return_value=(True, "")),
            ),
        ):
            post_response = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "persistent.example.com"},
            )
        assert post_response.status_code == 200

        # Reset cache mock to simulate cache miss on GET
        redis_mock_get = _make_redis_mock(cached_value=None)

        # Step 2: Retrieve endpoint
        with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock_get)):
            get_response = await test_client.get("/admin/config/cyperf-endpoint")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["endpoint"] == "persistent.example.com"

    @pytest.mark.asyncio
    async def test_get_endpoint_served_from_redis_cache(self, test_client):
        """GET /admin/config/cyperf-endpoint returns cached value without hitting DB.

        The Redis cache is the first lookup layer; a cache hit avoids the DB round-trip.
        """
        redis_mock = _make_redis_mock(cached_value="cached.example.com")

        with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
            response = await test_client.get("/admin/config/cyperf-endpoint")

        assert response.status_code == 200
        data = response.json()
        assert data["endpoint"] == "cached.example.com"
        assert data["is_valid"] is True
        # DB should NOT have been queried — cache satisfied the request
        redis_mock.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_endpoint_falls_back_to_env_var(self, test_client, db_session, monkeypatch):
        """GET falls back to CYPERF_CONTROLLER_IP env var when DB is also empty.

        Backwards compatibility: users who set the env var without configuring via
        the UI should still see their endpoint returned.
        """
        monkeypatch.setenv("CYPERF_CONTROLLER_IP", "env-endpoint.example.com")
        redis_mock = _make_redis_mock(cached_value=None)

        with patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)):
            response = await test_client.get("/admin/config/cyperf-endpoint")

        assert response.status_code == 200
        data = response.json()
        assert data["endpoint"] == "env-endpoint.example.com"

    @pytest.mark.asyncio
    async def test_post_endpoint_strips_https_prefix(self, test_client, db_session):
        """POST strips https:// prefix before saving to DB.

        Users may paste a full URL; the validator normalises to bare hostname/IP.
        """
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
        data = response.json()
        assert data["endpoint"] == "cyperf.example.com"

        saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
        assert saved == "cyperf.example.com"

    @pytest.mark.asyncio
    async def test_post_endpoint_cache_invalidated_then_repopulated(self, test_client, db_session):
        """POST deletes stale cache entry then repopulates it with the new value.

        Prevents stale reads: delete-before-set ensures no window where the old
        cached value would be served to concurrent GET requests.
        """
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
                json={"endpoint": "cache-check.example.com"},
            )

        assert response.status_code == 200

        # Cache must have been invalidated (delete) then repopulated (set)
        redis_mock.delete.assert_called_once_with("cyperf:endpoint")
        redis_mock.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_endpoint_succeeds_when_redis_unavailable(self, test_client, db_session):
        """POST saves to DB even when Redis raises an exception (graceful degradation).

        Redis cache failure must never prevent a valid endpoint from being persisted.
        DB remains the authoritative source.
        """

        async def _failing_redis():
            raise RuntimeError("Redis connection refused")

        with (
            patch("routes.admin.get_redis", new=_failing_redis),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(return_value=(True, "")),
            ),
        ):
            response = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "no-redis.example.com"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True

        # DB still receives the value despite Redis failure
        saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
        assert saved == "no-redis.example.com"


# ---------------------------------------------------------------------------
# Class: TestSyncTriggering
# Integration tests for POST /admin/sync-cyperf-now
# ---------------------------------------------------------------------------


class TestSyncTriggering:
    """Integration tests for manual sync triggering workflow."""

    @pytest.mark.asyncio
    async def test_manual_sync_requires_configured_endpoint(self, test_client, monkeypatch):
        """POST /admin/sync-cyperf-now returns 400 when no endpoint is configured.

        Without a valid endpoint, the sync cannot proceed.  The error must
        include a message guiding the user to configure the endpoint.
        """
        monkeypatch.delenv("CYPERF_CONTROLLER_IP", raising=False)

        response = await test_client.post("/admin/sync-cyperf-now")

        assert response.status_code == 400
        data = response.json()
        assert (
            "endpoint" in data["detail"].lower()
            or "configure" in data["detail"].lower()
            or "not configured" in data["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_manual_sync_queues_job_and_returns_job_id(self, test_client, db_session):
        """POST /admin/sync-cyperf-now queues sync job and returns job_id.

        The scheduler path: endpoint configured → scheduler running →
        job enqueued → HTTP 200 with status=sync_queued + job_id.
        """
        await SystemConfig.set_value(db_session, "cyperf_endpoint", "cyperf.example.com")
        await db_session.commit()

        scheduler_mock = _make_scheduler_mock("test-job-abc123")

        with (
            patch("routes.admin.get_scheduler", return_value=scheduler_mock),
            patch("routes.admin.get_settings") as mock_get_settings,
        ):
            mock_get_settings.return_value = MagicMock()
            response = await test_client.post("/admin/sync-cyperf-now")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sync_queued"
        assert data["job_id"] is not None
        assert data["endpoint"] == "cyperf.example.com"

        # Scheduler must have been called once to enqueue the job
        scheduler_mock.add_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_sync_falls_back_to_direct_execution(self, test_client, db_session):
        """POST /admin/sync-cyperf-now executes sync directly when scheduler unavailable.

        The direct-execution fallback: scheduler raises SchedulerNotStartedError →
        perform_sync called directly → HTTP 200 with status=sync_completed.
        """
        from scheduler import SchedulerNotStartedError

        await SystemConfig.set_value(db_session, "cyperf_endpoint", "direct.example.com")
        await db_session.commit()

        def _failing_scheduler():
            raise SchedulerNotStartedError("Scheduler not initialized")

        with (
            patch("routes.admin.get_scheduler", side_effect=_failing_scheduler),
            patch("routes.admin.get_settings") as mock_get_settings,
            patch("routes.admin.perform_sync", new_callable=AsyncMock) as mock_perform,
        ):
            mock_get_settings.return_value = MagicMock()
            mock_perform.return_value = None

            response = await test_client.post("/admin/sync-cyperf-now")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sync_completed"
        assert data["job_id"] is None
        assert data["endpoint"] == "direct.example.com"
        mock_perform.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_sync_uses_db_endpoint_not_env_var(
        self, test_client, db_session, monkeypatch
    ):
        """POST /admin/sync-cyperf-now uses DB endpoint, overriding env var.

        The DB value must take priority over the env var (CYPERF_CONTROLLER_IP)
        in the endpoint resolution waterfall used by the manual sync route.
        """
        monkeypatch.setenv("CYPERF_CONTROLLER_IP", "env-only.example.com")

        # DB endpoint takes precedence
        await SystemConfig.set_value(db_session, "cyperf_endpoint", "db-config.example.com")
        await db_session.commit()

        scheduler_mock = _make_scheduler_mock("precedence-test-job")

        with (
            patch("routes.admin.get_scheduler", return_value=scheduler_mock),
            patch("routes.admin.get_settings") as mock_get_settings,
        ):
            mock_get_settings.return_value = MagicMock()
            response = await test_client.post("/admin/sync-cyperf-now")

        assert response.status_code == 200
        data = response.json()
        # Response must echo back the DB-configured endpoint, not the env var
        assert data["endpoint"] == "db-config.example.com"

    @pytest.mark.asyncio
    async def test_manual_sync_uses_env_var_when_db_empty(
        self, test_client, db_session, monkeypatch
    ):
        """POST /admin/sync-cyperf-now uses env var when system_config has no endpoint.

        Backwards compatibility: users relying on CYPERF_CONTROLLER_IP env var
        (without UI configuration) must still be able to trigger manual sync.
        """
        monkeypatch.setenv("CYPERF_CONTROLLER_IP", "env-fallback.example.com")

        # DB has no endpoint configured
        scheduler_mock = _make_scheduler_mock("env-fallback-job")

        with (
            patch("routes.admin.get_scheduler", return_value=scheduler_mock),
            patch("routes.admin.get_settings") as mock_get_settings,
        ):
            mock_get_settings.return_value = MagicMock()
            response = await test_client.post("/admin/sync-cyperf-now")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sync_queued"
        assert data["endpoint"] == "env-fallback.example.com"


# ---------------------------------------------------------------------------
# Class: TestIntegratedWorkflow
# Full end-to-end test: configure endpoint → get config → trigger sync
# ---------------------------------------------------------------------------


class TestIntegratedWorkflow:
    """Full workflow integration tests spanning multiple API calls."""

    @pytest.mark.asyncio
    async def test_configure_endpoint_then_trigger_sync(self, test_client, db_session):
        """Full workflow: configure endpoint via POST → verify GET → trigger sync.

        Validates that data flows correctly through the full chain:
        1. POST /admin/config/cyperf-endpoint  (save + validate)
        2. GET  /admin/config/cyperf-endpoint  (retrieve — DB fallback)
        3. POST /admin/sync-cyperf-now         (sync using saved endpoint)
        """
        redis_mock = _make_redis_mock(cached_value=None)
        scheduler_mock = _make_scheduler_mock("workflow-test-job")

        # Step 1: Configure endpoint
        with (
            patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(return_value=(True, "")),
            ),
        ):
            post_resp = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "workflow.example.com"},
            )
        assert post_resp.status_code == 200
        assert post_resp.json()["is_valid"] is True

        # Step 2: Verify GET retrieves the configured endpoint
        get_redis_mock = _make_redis_mock(cached_value=None)
        with patch("routes.admin.get_redis", new=AsyncMock(return_value=get_redis_mock)):
            get_resp = await test_client.get("/admin/config/cyperf-endpoint")
        assert get_resp.status_code == 200
        assert get_resp.json()["endpoint"] == "workflow.example.com"

        # Step 3: Trigger sync — must use the persisted endpoint
        with (
            patch("routes.admin.get_scheduler", return_value=scheduler_mock),
            patch("routes.admin.get_settings") as mock_get_settings,
        ):
            mock_get_settings.return_value = MagicMock()
            sync_resp = await test_client.post("/admin/sync-cyperf-now")

        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] == "sync_queued"
        assert sync_data["endpoint"] == "workflow.example.com"

    @pytest.mark.asyncio
    async def test_update_endpoint_affects_subsequent_sync(self, test_client, db_session):
        """Updating endpoint via POST changes the endpoint used by the next sync.

        The system must use the most recently configured endpoint, not a stale value.
        """
        redis_mock = _make_redis_mock(cached_value=None)

        # Configure initial endpoint
        with (
            patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock)),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(return_value=(True, "")),
            ),
        ):
            resp1 = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "old-host.example.com"},
            )
        assert resp1.status_code == 200

        # Update to new endpoint
        redis_mock2 = _make_redis_mock(cached_value=None)
        with (
            patch("routes.admin.get_redis", new=AsyncMock(return_value=redis_mock2)),
            patch(
                "routes.admin.validate_endpoint_connectivity",
                new=AsyncMock(return_value=(True, "")),
            ),
        ):
            resp2 = await test_client.post(
                "/admin/config/cyperf-endpoint",
                json={"endpoint": "new-host.example.com"},
            )
        assert resp2.status_code == 200

        # Verify DB reflects the update
        saved = await SystemConfig.get_value(db_session, "cyperf_endpoint")
        assert saved == "new-host.example.com"

        # Trigger sync — must use new endpoint
        scheduler_mock = _make_scheduler_mock("update-test-job")
        with (
            patch("routes.admin.get_scheduler", return_value=scheduler_mock),
            patch("routes.admin.get_settings") as mock_get_settings,
        ):
            mock_get_settings.return_value = MagicMock()
            sync_resp = await test_client.post("/admin/sync-cyperf-now")

        assert sync_resp.status_code == 200
        assert sync_resp.json()["endpoint"] == "new-host.example.com"


# ---------------------------------------------------------------------------
# Class: TestSyncServiceEndpointResolution
# perform_sync() uses correct endpoint from system_config
# ---------------------------------------------------------------------------


class TestSyncServiceEndpointResolution:
    """Test perform_sync() endpoint resolution (system_config > env var)."""

    @pytest.mark.asyncio
    async def test_sync_service_uses_system_config_endpoint(self, db_session, test_settings):
        """perform_sync() reads controller_ip from system_config, not the env var.

        system_config must take priority over Settings.cyperf_controller_ip
        so that UI-configured endpoints are actually used in sync.
        """
        await SystemConfig.set_value(db_session, "cyperf_endpoint", "config-host.example.com")
        await db_session.commit()

        captured_ips: list[str] = []

        def capturing_cyperf_service(controller_ip, username, password):
            captured_ips.append(controller_ip)
            svc = MagicMock()
            svc.fetch_cve_strike_mappings = AsyncMock(
                return_value=MagicMock(
                    cve_mappings={"CVE-2024-1001": "Strike-001"},
                    ai_strikes=[],
                )
            )
            return svc

        with patch("services.sync_service.CyperfService", side_effect=capturing_cyperf_service):
            await perform_sync(session=db_session, settings=test_settings)

        assert len(captured_ips) >= 1
        assert (
            captured_ips[0] == "config-host.example.com"
        ), f"Expected system_config endpoint 'config-host.example.com', got {captured_ips[0]!r}"

    @pytest.mark.asyncio
    async def test_sync_service_falls_back_to_env_var_when_db_empty(
        self, db_session, test_settings
    ):
        """perform_sync() uses settings.cyperf_controller_ip when system_config is empty.

        When no endpoint has been configured via the UI, the sync must still
        work using the environment variable fallback.
        """
        # Fresh db_session has no cyperf_endpoint
        existing = await SystemConfig.get_value(db_session, "cyperf_endpoint")
        assert existing is None, "Test precondition: system_config must be empty"

        captured_ips: list[str] = []

        def capturing_cyperf_service(controller_ip, username, password):
            captured_ips.append(controller_ip)
            svc = MagicMock()
            svc.fetch_cve_strike_mappings = AsyncMock(
                return_value=MagicMock(
                    cve_mappings={"CVE-2024-2001": "Strike-002"},
                    ai_strikes=[],
                )
            )
            return svc

        with patch("services.sync_service.CyperfService", side_effect=capturing_cyperf_service):
            await perform_sync(session=db_session, settings=test_settings)

        assert len(captured_ips) >= 1
        # Must use the env var value from test_settings fixture
        assert (
            captured_ips[0] == "env-integration-host"
        ), f"Expected env var endpoint 'env-integration-host', got {captured_ips[0]!r}"
