"""Tests for NVD rate-limit fallback behavior.

Covers: SYNC-05 (NVD rate-limit -> HTTP 200, no 500)
Architecture invariant: NVD 429 must never surface as HTTP 500.
"""

from unittest.mock import MagicMock

import pytest

from services.nvd_service import NVDRateLimitError


@pytest.mark.asyncio
async def test_nvd_rate_limit_with_cache_returns_200(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """SYNC-05: When NVD is rate-limited and cache has data, API returns HTTP 200.

    This is the critical path — a 500 here violates the architecture invariant.
    """
    # NVD is rate-limited
    mock_nvd_client.fetch_cve.side_effect = NVDRateLimitError("Rate limited")

    # But cache has the CVE
    mock_cache_service._store["CVE-2024-1234"] = sample_cve_dict
    mock_cache_service._ttl_store["CVE-2024-1234"] = 80000

    response = await test_client.get("/cve/search?id=CVE-2024-1234")

    # Must be 200, not 429, not 500, not 503
    assert response.status_code == 200, (
        f"Expected 200 on rate-limit with cache hit, got {response.status_code}: "
        f"{response.text}"
    )
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_nvd_rate_limit_no_cache_returns_503_or_404(
    test_client, mock_cache_service, mock_nvd_client
):
    """When NVD is rate-limited AND no cached data exists, API returns 503 or 404.

    503 = service temporarily unavailable.
    404 = CVE genuinely not found (acceptable fallback).
    500 = our bug — MUST NOT occur.
    """
    mock_nvd_client.fetch_cve.side_effect = NVDRateLimitError("Rate limited")
    mock_cache_service.get.return_value = None  # no cache

    response = await test_client.get("/cve/search?id=CVE-2099-99999")

    # 503 or 404 are acceptable; 500 is NOT
    assert response.status_code in (
        503,
        404,
    ), f"Expected 503 or 404 when NVD down + no cache, got {response.status_code}"
    assert response.status_code != 500, "HTTP 500 must never be returned on NVD rate-limit"


@pytest.mark.asyncio
async def test_nvd_rate_limit_latest_serves_db_cache(test_client, mock_nvd_client):
    """SYNC-05: /cve/latest with NVD rate-limited serves from DB (empty on fresh start).

    Response is always HTTP 200 with empty or partial results — never 500.
    """
    mock_nvd_client.fetch_latest.side_effect = NVDRateLimitError("Rate limited")

    response = await test_client.get("/cve/latest")

    # Must not be 500 regardless of NVD state
    assert (
        response.status_code == 200
    ), f"Expected 200 on /cve/latest with NVD down, got {response.status_code}"


@pytest.mark.asyncio
async def test_redis_down_falls_back_to_nvd(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """Redis failure must not bring down the API.

    Falls back to NVD fetch and returns data.
    """
    mock_cache_service.get.return_value = None  # Redis failure returns None

    # Mock the NVD object attributes
    nvd_obj = MagicMock()
    nvd_obj.id = "CVE-2024-1234"
    nvd_obj.published = "2024-01-15T10:00:00.000"
    nvd_obj.descriptions = [MagicMock(lang="en", value="Test")]
    nvd_obj.references = []
    nvd_obj.v31score = 9.8
    nvd_obj.v31severity = "CRITICAL"
    nvd_obj.v31vector = "CVSS:3.1/AV:N"
    nvd_obj.v30score = None
    nvd_obj.v30severity = None
    nvd_obj.v30vector = None
    nvd_obj.v40score = None
    nvd_obj.v40severity = None
    nvd_obj.v40vector = None
    mock_nvd_client.fetch_cve.return_value = nvd_obj

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200
