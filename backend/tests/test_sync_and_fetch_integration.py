"""Integration tests: perform_sync() -> ai_cves table -> GET /ai-cves endpoint.

Validates the complete data flow using in-memory SQLite (via conftest fixtures)
and the Cyperf service patching pattern from test_cyperf_integration.py.

Test cases:
  1. sync populates ai_cves table; GET /ai-cves returns the rows
  2. full-replace: sync clears stale rows and writes fresh rows
  3. graceful degradation: failed sync retains existing ai_cves rows

All tests patch services.cyperf_service.cyperf to avoid real network calls.
asyncio.sleep is patched in cases where the 3-retry loop would add 5s delay.
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from config import Settings
from db.ai_cves import AICve
from services.sync_service import perform_sync

# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_cve_strike(strike_name: str, cve_num: str) -> dict:
    """Build a mock Cyperf CVE strike payload (Type='CVE' reference)."""
    return {
        "Name": strike_name,
        "Metadata": {"References": [{"Type": "CVE", "Value": cve_num}]},
    }


def _make_ai_strike(strike_name: str) -> dict:
    """Build a mock Cyperf AI strike payload (url-only reference, no Type='CVE')."""
    return {
        "Name": strike_name,
        "Metadata": {"References": [{"Type": "url", "Value": "https://example.com/ai-paper"}]},
    }


def _page(strikes: list[dict]) -> MagicMock:
    """Build a mock API page response for the given strike list."""
    r = MagicMock()
    r.to_json.return_value = json.dumps({"data": strikes})
    return r


def _empty_page() -> MagicMock:
    """Build a mock empty-page response (signals end of pagination)."""
    r = MagicMock()
    r.to_json.return_value = json.dumps({"data": []})
    return r


def _patch_cyperf(strikes_side_effect):
    """Return a context manager that patches services.cyperf_service.cyperf.

    strikes_side_effect: list of mock responses returned in sequence by
    mock_api_instance.get_resources_strikes().
    """
    mock_cyperf = MagicMock()
    mock_api_client = MagicMock()
    mock_api_instance = MagicMock()
    mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
    mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
    mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
    mock_api_instance.get_resources_strikes.side_effect = strikes_side_effect
    return patch("services.cyperf_service.cyperf", mock_cyperf)


@pytest.fixture
def test_settings() -> Settings:
    """Minimal Settings for sync tests — no real Cyperf controller needed."""
    return Settings(
        cyperf_controller_ip="test-host",
        cyperf_username="test-user",
        cyperf_password="test-password",
        cyperf_sync_interval_hours=24,
        database_url="sqlite+aiosqlite:///:memory:",
    )


# ─── Test 1: Sync populates endpoint ────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_populates_ai_cves_then_endpoint_returns_them(
    test_client,
    db_session,
    test_settings,
):
    """After perform_sync(), GET /ai-cves returns the AI strike that was written.

    Payload: 1 CVE strike (satisfies cves_count > 0 guard) + 1 AI strike.
    """
    strikes = [
        _make_cve_strike("CVE-Strike-A", "2024-9001"),
        _make_ai_strike("Strike AI LLM SQL Injection Jailbreak - Test"),
    ]

    with _patch_cyperf([_page(strikes), _empty_page()]):
        await perform_sync(session=db_session, settings=test_settings)

    response = await test_client.get("/ai-cves")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] >= 1, "At least 1 AI strike should be present after sync"

    ai_names = [r["ai_strike_name"] for r in body["results"]]
    assert "Strike AI LLM SQL Injection Jailbreak - Test" in ai_names

    # id must follow NoCVE_cyperf prefix convention
    for row in body["results"]:
        assert row["id"].startswith("NoCVE_cyperf"), f"Unexpected id format: {row['id']}"


# ─── Test 2: Full-replace clears stale rows ─────────────────────────────────


@pytest.mark.asyncio
async def test_sync_clears_then_repopulates_ai_cves(
    test_client,
    db_session,
    test_settings,
):
    """Second sync full-replaces ai_cves: stale row gone, fresh row present."""
    # Pre-insert a stale row directly
    stale_row = AICve(
        id=str(uuid.uuid4()),
        cve_id=f"NoCVE_cyperf{uuid.uuid4()}",
        strike_name="Stale-Strike",
        strike_type="ai_attack",
        metadata_json=None,
    )
    db_session.add(stale_row)
    await db_session.commit()

    # Verify stale row is visible before sync
    pre_sync = await test_client.get("/ai-cves")
    stale_names = [r["ai_strike_name"] for r in pre_sync.json()["results"]]
    assert "Stale-Strike" in stale_names, "Stale row must exist before sync"

    # Run sync with fresh AI strike + at least one CVE strike
    fresh_strikes = [
        _make_cve_strike("CVE-Strike-Fresh", "2024-0002"),
        _make_ai_strike("Fresh-Strike"),
    ]

    with _patch_cyperf([_page(fresh_strikes), _empty_page()]):
        await perform_sync(session=db_session, settings=test_settings)

    # After sync: stale row must be gone, fresh row must be present
    post_sync = await test_client.get("/ai-cves")
    assert post_sync.status_code == 200
    post_names = [r["ai_strike_name"] for r in post_sync.json()["results"]]

    assert "Stale-Strike" not in post_names, "Stale row must be removed by full-replace"
    assert "Fresh-Strike" in post_names, "Fresh row must be present after sync"


# ─── Test 3: Graceful degradation — failed sync retains existing rows ────────


@pytest.mark.asyncio
async def test_failed_sync_retains_existing_ai_cves(
    test_client,
    db_session,
    test_settings,
):
    """When Cyperf is unreachable, existing ai_cves rows are preserved.

    asyncio.sleep is patched to avoid 5s delay from the retry loop's
    third attempt delay (perform_sync sleeps 5s before final retry).
    """
    # Pre-insert a row that should survive the failed sync
    retained_row = AICve(
        id=str(uuid.uuid4()),
        cve_id=f"NoCVE_cyperf{uuid.uuid4()}",
        strike_name="Retained-Strike",
        strike_type="ai_attack",
        metadata_json=None,
    )
    db_session.add(retained_row)
    await db_session.commit()

    # Simulate Cyperf completely unreachable — all 3 retry attempts fail
    with _patch_cyperf(ConnectionError("Controller unreachable")):
        with patch("services.sync_service.asyncio.sleep", return_value=None):
            await perform_sync(session=db_session, settings=test_settings)

    # After failed sync: the pre-existing row must still be there
    response = await test_client.get("/ai-cves")
    assert response.status_code == 200
    body = response.json()

    retained_names = [r["ai_strike_name"] for r in body["results"]]
    assert (
        "Retained-Strike" in retained_names
    ), "Graceful degradation: existing rows must survive a failed sync"
