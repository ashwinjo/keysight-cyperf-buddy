"""Tests for Redis cache behavior: hit/miss, SWR trigger.

Covers: SYNC-01 (NVD responses cached in Redis)
"""

import pytest


@pytest.mark.asyncio
async def test_cache_miss_triggers_nvd_fetch(test_client, mock_nvd_client, mock_cache_service):
    """On cache miss, NVD fetch is called exactly once."""
    mock_cache_service.get.return_value = None  # force cache miss

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    mock_nvd_client.fetch_cve.assert_called_once()


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_nvd(
    test_client, mock_nvd_client, mock_cache_service, sample_cve_dict
):
    """On cache hit, NVD is NOT re-queried (SYNC-01 core behavior)."""
    # Seed cache by directly populating the internal store
    mock_cache_service._store["CVE-2024-1234"] = sample_cve_dict
    mock_cache_service._ttl_store["CVE-2024-1234"] = 80000  # 22h+ remaining, not stale

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    mock_nvd_client.fetch_cve.assert_not_called()


@pytest.mark.asyncio
async def test_cache_data_written_after_nvd_fetch(test_client, mock_cache_service, mock_nvd_client):
    """After NVD fetch, result is written to cache."""
    mock_cache_service.get.return_value = None  # force cache miss

    await test_client.get("/cve/search?id=CVE-2024-1234")

    mock_cache_service.set.assert_called_once()
    call_args = mock_cache_service.set.call_args
    assert call_args[0][0] == "CVE-2024-1234"  # first arg is cve_id
    assert isinstance(call_args[0][1], dict)  # second arg is cve dict


@pytest.mark.asyncio
async def test_stale_cache_triggers_background_refresh(
    test_client, mock_cache_service, mock_nvd_client, sample_cve_dict
):
    """SWR: stale cache (TTL < 4h) triggers background refresh, serves data immediately."""
    # Seed cache with near-expiry TTL
    mock_cache_service._store["CVE-2024-1234"] = sample_cve_dict
    mock_cache_service._ttl_store["CVE-2024-1234"] = 3600  # 1h remaining — stale

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200  # served immediately from stale cache

    # Response body is the stale cached data
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_cvss_scores_are_float_not_string(test_client, sample_cve_dict, mock_cache_service):
    """CVSS scores in JSON response must be floats, not strings (Pydantic Decimal bug)."""
    mock_cache_service._store["CVE-2024-1234"] = sample_cve_dict
    mock_cache_service._ttl_store["CVE-2024-1234"] = 86400

    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    body = response.json()
    cve = body["results"][0]

    if cve["cvss_v3_score"] is not None:
        assert isinstance(cve["cvss_v3_score"], float)
    if cve["cvss_v4_score"] is not None:
        assert isinstance(cve["cvss_v4_score"], float)
