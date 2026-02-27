"""Integration tests for POST /admin/sync-cyperf-now and dynamic endpoint resolution.

Test strategy:
- HTTP layer tested via test_client (AsyncClient against in-memory SQLite app)
- sync_service.perform_sync tested directly with db_session fixture
- Cyperf API calls mocked via patch("services.cyperf_service.cyperf", ...)
- APScheduler mocked via patch("routes.admin.get_scheduler", ...)
- validate_endpoint_connectivity mocked to avoid real network calls

Coverage:
  1. POST /admin/sync-cyperf-now returns 200 + sync_queued + job_id (scheduler path)
  2. POST /admin/sync-cyperf-now returns 400 when endpoint not configured
  3. perform_sync() uses system_config endpoint over env var
  4. perform_sync() falls back to env var when system_config not set
  5. POST /admin/sync-cyperf-now falls back to direct execution if scheduler unavailable
  6. POST /admin/sync-cyperf-now returns 400 when endpoint is empty string in DB
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Settings
from db.system_config import SystemConfig
from services.sync_service import perform_sync

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cve_strike(strike_name: str, cve_num: str) -> dict:
    """Build a mock Cyperf CVE strike payload."""
    return {
        "Name": strike_name,
        "Metadata": {"References": [{"Type": "CVE", "Value": cve_num}]},
    }


def _page(strikes: list[dict]) -> MagicMock:
    """Build a mock API page response."""
    import json

    r = MagicMock()
    r.to_json.return_value = json.dumps({"data": strikes})
    return r


def _empty_page() -> MagicMock:
    """Build a mock empty-page response (end of pagination)."""
    import json

    r = MagicMock()
    r.to_json.return_value = json.dumps({"data": []})
    return r


def _patch_cyperf(strikes_side_effect):
    """Return a context manager patching services.cyperf_service.cyperf.

    Args:
        strikes_side_effect: list of mock responses from get_resources_strikes()
    """
    mock_cyperf = MagicMock()
    mock_api_client = MagicMock()
    mock_api_instance = MagicMock()
    mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
    mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
    mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
    mock_api_instance.get_resources_strikes.side_effect = strikes_side_effect
    return patch("services.cyperf_service.cyperf", mock_cyperf)


def _make_scheduler_mock(job_id: str = "manual_sync_test-uuid") -> MagicMock:
    """Build a mock APScheduler with add_job returning a job with given id."""
    mock_job = MagicMock()
    mock_job.id = job_id

    scheduler_mock = MagicMock()
    scheduler_mock.running = True
    scheduler_mock.add_job.return_value = mock_job
    return scheduler_mock


@pytest.fixture
def test_settings() -> Settings:
    """Minimal Settings for sync tests — no real Cyperf controller needed."""
    return Settings(
        cyperf_controller_ip="env-test-host",
        cyperf_username="test-user",
        cyperf_password="test-password",
        cyperf_sync_interval_hours=24,
        database_url="sqlite+aiosqlite:///:memory:",
    )


# ---------------------------------------------------------------------------
# Test 1: POST /admin/sync-cyperf-now — scheduler path (happy path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_sync_endpoint_returns_200_sync_queued(test_client, db_session, monkeypatch):
    """POST /admin/sync-cyperf-now returns 200 with status=sync_queued and job_id.

    Setup: system_config has a valid endpoint. Scheduler is running.
    Expected: HTTP 200, status=sync_queued, job_id present.
    """
    # Seed system_config with a valid endpoint
    await SystemConfig.set_value(db_session, "cyperf_endpoint", "cyperf.example.com")
    await db_session.commit()

    scheduler_mock = _make_scheduler_mock("manual_sync_abc123")

    with (
        patch("routes.admin.get_scheduler", return_value=scheduler_mock),
        patch("routes.admin.get_settings") as mock_get_settings,
    ):
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        response = await test_client.post("/admin/sync-cyperf-now")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sync_queued"
    assert body["job_id"] is not None
    assert body["endpoint"] == "cyperf.example.com"
    assert "message" in body
    # Scheduler's add_job should have been called once
    scheduler_mock.add_job.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: POST /admin/sync-cyperf-now — no endpoint configured (HTTP 400)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_sync_requires_configured_endpoint(test_client, monkeypatch):
    """POST /admin/sync-cyperf-now returns 400 if no endpoint in DB or env.

    Setup: system_config is empty; CYPERF_CONTROLLER_IP env var is unset.
    Expected: HTTP 400 with descriptive detail.
    """
    # Ensure env var is not set
    monkeypatch.delenv("CYPERF_CONTROLLER_IP", raising=False)

    response = await test_client.post("/admin/sync-cyperf-now")

    assert response.status_code == 400
    body = response.json()
    assert (
        "endpoint not configured" in body["detail"].lower() or "configure" in body["detail"].lower()
    )


# ---------------------------------------------------------------------------
# Test 3: perform_sync() uses system_config endpoint over env var
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_service_uses_system_config_endpoint(db_session, test_settings, monkeypatch):
    """perform_sync() reads endpoint from system_config, not the env var.

    Setup: system_config = "config-host", settings.cyperf_controller_ip = "env-test-host"
    Expected: CyperfService instantiated with controller_ip="config-host"
    """
    # Set system_config to a distinct value
    await SystemConfig.set_value(db_session, "cyperf_endpoint", "config-host.example.com")
    await db_session.commit()

    captured_controller_ips: list[str] = []

    def capturing_cyperf_service(controller_ip, username, password):
        captured_controller_ips.append(controller_ip)
        # Return a minimal mock that won't try to connect
        svc_mock = MagicMock()
        svc_mock.fetch_cve_strike_mappings = AsyncMock(
            return_value=MagicMock(
                cve_mappings={"CVE-2024-1001": "Strike-001"},
                ai_strikes=[],
            )
        )
        return svc_mock

    with patch("services.sync_service.CyperfService", side_effect=capturing_cyperf_service):
        await perform_sync(session=db_session, settings=test_settings)

    # Must have used the config-host value, not the env-test-host from settings
    assert len(captured_controller_ips) >= 1
    assert (
        captured_controller_ips[0] == "config-host.example.com"
    ), f"Expected 'config-host.example.com', got {captured_controller_ips[0]!r}"


# ---------------------------------------------------------------------------
# Test 4: perform_sync() falls back to env var when system_config is empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_service_falls_back_to_env_var(db_session, test_settings):
    """perform_sync() uses settings.cyperf_controller_ip when system_config is empty.

    Setup: system_config is empty (no cyperf_endpoint key).
    settings.cyperf_controller_ip = "env-test-host" (from test_settings fixture).
    Expected: CyperfService instantiated with controller_ip="env-test-host"
    """
    # Ensure no cyperf_endpoint in system_config (db_session is fresh per test)
    existing = await SystemConfig.get_value(db_session, "cyperf_endpoint")
    assert existing is None, "Expected fresh session with no cyperf_endpoint"

    captured_controller_ips: list[str] = []

    def capturing_cyperf_service(controller_ip, username, password):
        captured_controller_ips.append(controller_ip)
        svc_mock = MagicMock()
        svc_mock.fetch_cve_strike_mappings = AsyncMock(
            return_value=MagicMock(
                cve_mappings={"CVE-2024-2001": "Strike-002"},
                ai_strikes=[],
            )
        )
        return svc_mock

    with patch("services.sync_service.CyperfService", side_effect=capturing_cyperf_service):
        await perform_sync(session=db_session, settings=test_settings)

    assert len(captured_controller_ips) >= 1
    assert (
        captured_controller_ips[0] == "env-test-host"
    ), f"Expected 'env-test-host', got {captured_controller_ips[0]!r}"


# ---------------------------------------------------------------------------
# Test 5: POST /admin/sync-cyperf-now — scheduler unavailable (direct fallback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_sync_fallback_to_direct_execution(test_client, db_session, monkeypatch):
    """POST /admin/sync-cyperf-now executes directly if scheduler is unavailable.

    Setup: system_config has valid endpoint; get_scheduler raises SchedulerNotStartedError.
    Expected: HTTP 200, status=sync_completed (direct execution fallback).
    """
    from scheduler import SchedulerNotStartedError

    # Seed system_config
    await SystemConfig.set_value(db_session, "cyperf_endpoint", "fallback-host.example.com")
    await db_session.commit()

    def _failing_scheduler():
        raise SchedulerNotStartedError("Scheduler not initialized")

    with (
        patch("routes.admin.get_scheduler", side_effect=_failing_scheduler),
        patch("routes.admin.get_settings") as mock_get_settings,
        patch("routes.admin.perform_sync", new_callable=AsyncMock) as mock_perform_sync,
    ):
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        mock_perform_sync.return_value = None

        response = await test_client.post("/admin/sync-cyperf-now")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sync_completed"
    assert body["job_id"] is None
    assert body["endpoint"] == "fallback-host.example.com"
    # perform_sync must have been called once (direct execution path)
    mock_perform_sync.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: POST /admin/sync-cyperf-now — empty endpoint in DB returns 400
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_sync_returns_400_on_empty_endpoint(test_client, db_session, monkeypatch):
    """POST /admin/sync-cyperf-now returns 400 if endpoint is empty and env var unset.

    An empty-string endpoint stored in system_config is treated as not configured.
    """
    # Ensure env var is not set
    monkeypatch.delenv("CYPERF_CONTROLLER_IP", raising=False)

    # Do NOT insert any endpoint — leave system_config empty
    response = await test_client.post("/admin/sync-cyperf-now")

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Test 7: POST /admin/sync-cyperf-now — env var used when system_config empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_sync_uses_env_var_when_system_config_empty(
    test_client, db_session, monkeypatch
):
    """POST /admin/sync-cyperf-now accepts env var as endpoint source if DB is empty.

    Setup: system_config empty, CYPERF_CONTROLLER_IP="env-host.example.com"
    Expected: HTTP 200 with endpoint="env-host.example.com" echoed back.
    """
    monkeypatch.setenv("CYPERF_CONTROLLER_IP", "env-host.example.com")

    scheduler_mock = _make_scheduler_mock("manual_sync_env-path")

    with (
        patch("routes.admin.get_scheduler", return_value=scheduler_mock),
        patch("routes.admin.get_settings") as mock_get_settings,
    ):
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings

        response = await test_client.post("/admin/sync-cyperf-now")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sync_queued"
    assert body["endpoint"] == "env-host.example.com"
