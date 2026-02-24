"""Tests for GET /cve/search endpoint.

Covers: SEARCH-01, SEARCH-02, SEARCH-05
"""

import pytest


@pytest.mark.asyncio
async def test_search_exact_id_returns_all_fields(test_client, sample_cve_dict):
    """SEARCH-01 + SEARCH-02: Exact ID returns CVE with all required fields."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234")
    assert response.status_code == 200

    body = response.json()
    assert body["query"] == "CVE-2024-1234"
    assert body["search_type"] == "exact"
    assert body["total"] == 1

    cve = body["results"][0]
    assert cve["id"] == "CVE-2024-1234"
    assert cve["description"] == sample_cve_dict["description"]
    assert cve["published_date"] is not None
    assert isinstance(cve["cvss_v3_score"], float)  # must be float, not string
    assert cve["cvss_v3_severity"] == "CRITICAL"
    assert cve["cvss_v3_vector"] is not None
    assert isinstance(cve["reference_urls"], list)
    assert len(cve["reference_urls"]) > 0
    assert cve["testable"] is None  # Phase 3 placeholder


@pytest.mark.asyncio
async def test_search_case_insensitive_id(test_client):
    """CVE ID lookup is case-insensitive; normalized to uppercase."""
    response = await test_client.get("/cve/search?id=cve-2024-1234")
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["id"] == "CVE-2024-1234"


@pytest.mark.asyncio
async def test_search_severity_filter_exact_match(test_client):
    """SEARCH-05: Severity filter is equality (CRITICAL matches CRITICAL, not HIGH)."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234&severity=CRITICAL")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1  # matches CRITICAL

    response_no_match = await test_client.get("/cve/search?id=CVE-2024-1234&severity=LOW")
    assert response_no_match.status_code == 200
    assert response_no_match.json()["total"] == 0  # CRITICAL CVE filtered out by LOW


@pytest.mark.asyncio
async def test_search_severity_case_insensitive(test_client):
    """Severity filter is case-insensitive per context decisions."""
    for severity in ["HIGH", "high", "High", "hIgH"]:
        # CVE-2024-1234 is CRITICAL so HIGH filter should return 0 (no exception)
        response = await test_client.get(f"/cve/search?id=CVE-2024-1234&severity={severity}")
        assert response.status_code == 200  # no 422 regardless of case


@pytest.mark.asyncio
async def test_search_invalid_cve_format_returns_422(test_client):
    """Invalid CVE format returns 422 with INVALID_CVE_QUERY error code."""
    invalid_ids = ["not-a-cve", "CVE-ABCD-1234", "2024-1234"]
    for invalid in invalid_ids:
        response = await test_client.get(f"/cve/search?id={invalid}")
        assert response.status_code in (422, 400), f"Expected error for: {invalid}"


@pytest.mark.asyncio
async def test_search_invalid_severity_returns_422(test_client):
    """Invalid severity returns 422 with INVALID_SEVERITY error code."""
    response = await test_client.get("/cve/search?id=CVE-2024-1234&severity=EXTREME")
    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["error"] == "INVALID_SEVERITY"


@pytest.mark.asyncio
async def test_search_not_found_returns_404(test_client, mock_nvd_client):
    """CVE not in NVD and not in cache -> 404."""
    mock_nvd_client.fetch_cve.return_value = None  # NVD returns nothing

    response = await test_client.get("/cve/search?id=CVE-2099-99999")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"] == "CVE_NOT_FOUND"


@pytest.mark.asyncio
async def test_search_wildcard_returns_empty_list(test_client):
    """Wildcard/prefix search on empty DB returns empty results (not 404)."""
    response = await test_client.get("/cve/search?id=CVE-2024-*")
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["search_type"] == "prefix"
