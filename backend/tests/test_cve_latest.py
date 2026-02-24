"""Tests for GET /cve/latest endpoint.

Covers: BROWSE-01, BROWSE-02, BROWSE-04
"""

import pytest


@pytest.mark.asyncio
async def test_latest_returns_paginated_results(test_client):
    """BROWSE-01: /cve/latest returns results with pagination metadata."""
    response = await test_client.get("/cve/latest")
    assert response.status_code == 200

    body = response.json()
    assert "results" in body
    assert "page" in body
    assert "page_size" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 50  # default


@pytest.mark.asyncio
async def test_latest_results_include_required_fields(test_client):
    """BROWSE-04: Each result includes CVE ID, CVSS score, published date, testability."""
    response = await test_client.get("/cve/latest")
    body = response.json()

    if body["results"]:
        row = body["results"][0]
        # BROWSE-04 required fields
        assert "id" in row
        assert "cvss_v3_score" in row or "cvss_v4_score" in row
        assert "published_date" in row
        assert "testable" in row  # Phase 3 populates; None is valid in Phase 2


@pytest.mark.asyncio
async def test_latest_pagination_parameters(test_client):
    """Pagination parameters are reflected in response."""
    response = await test_client.get("/cve/latest?page=2&limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 10


@pytest.mark.asyncio
async def test_latest_limit_max_500(test_client):
    """Limit above 500 is rejected with 422."""
    response = await test_client.get("/cve/latest?limit=501")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_latest_severity_filter(test_client):
    """SEARCH-05 on browse: severity filter applied; case-insensitive."""
    response_high = await test_client.get("/cve/latest?severity=HIGH")
    assert response_high.status_code == 200
    body = response_high.json()
    assert body["severity_filter"] == "HIGH"

    # All returned CVEs must have HIGH severity in v3.1 or v4.0
    for cve in body["results"]:
        has_high = (
            cve.get("cvss_v3_severity") == "HIGH" or cve.get("cvss_v4_severity") == "HIGH"
        )
        assert has_high, f"CVE {cve['id']} does not match HIGH severity"


@pytest.mark.asyncio
async def test_latest_severity_lowercase_accepted(test_client):
    """Severity filter is case-insensitive per context decisions."""
    response = await test_client.get("/cve/latest?severity=critical")
    assert response.status_code == 200
    assert response.json()["severity_filter"] == "CRITICAL"


@pytest.mark.asyncio
async def test_latest_invalid_severity_returns_422(test_client):
    """Invalid severity on /cve/latest returns 422."""
    response = await test_client.get("/cve/latest?severity=UNKNOWN")
    assert response.status_code == 422
