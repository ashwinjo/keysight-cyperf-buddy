"""Unit tests for GET /ai-cves endpoint.

Covers:
  1. Empty table → 200 with {"results": [], "total": 0}
  2. Inserted rows are returned with correct id and ai_strike_name
  3. Pagination (page/limit) returns subset, total reflects full count
  4. strike_type filter returns only matching rows
  5. Response shape matches AiCVEResponse schema fields
"""

import uuid

import pytest

from db.ai_cves import AICve


def _make_ai_cve(
    strike_name: str = "Test-Strike",
    strike_type: str = "ai_attack",
) -> AICve:
    """Build an AICve ORM row with synthetic NoCVE_cyperf ID."""
    return AICve(
        id=str(uuid.uuid4()),
        cve_id=f"NoCVE_cyperf{uuid.uuid4()}",
        strike_name=strike_name,
        strike_type=strike_type,
        metadata_json=None,
    )


# ─── Test 1: Empty table ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_ai_cves_empty_table(test_client):
    """GET /ai-cves on empty DB returns 200 with empty results and total=0."""
    response = await test_client.get("/ai-cves")
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["total"] == 0


# ─── Test 2: Rows returned ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_ai_cves_returns_inserted_rows(test_client, db_session):
    """3 inserted AICve rows are all returned; id and ai_strike_name are correct."""
    rows = [
        _make_ai_cve(strike_name="Strike-Alpha"),
        _make_ai_cve(strike_name="Strike-Beta"),
        _make_ai_cve(strike_name="Strike-Gamma"),
    ]
    for row in rows:
        db_session.add(row)
    await db_session.commit()

    response = await test_client.get("/ai-cves")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 3
    assert len(body["results"]) == 3

    returned_names = {r["ai_strike_name"] for r in body["results"]}
    assert returned_names == {"Strike-Alpha", "Strike-Beta", "Strike-Gamma"}

    # id must equal cve_id (not the uuid4 surrogate PK)
    returned_ids = {r["id"] for r in body["results"]}
    inserted_cve_ids = {row.cve_id for row in rows}
    assert returned_ids == inserted_cve_ids


# ─── Test 3: Pagination ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_ai_cves_pagination(test_client, db_session):
    """page=1&limit=2 returns 2 results; total remains 5."""
    for i in range(5):
        db_session.add(_make_ai_cve(strike_name=f"Strike-{i}"))
    await db_session.commit()

    response = await test_client.get("/ai-cves?page=1&limit=2")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 5
    assert len(body["results"]) == 2


@pytest.mark.asyncio
async def test_list_ai_cves_page2_returns_next_batch(test_client, db_session):
    """page=2&limit=2 returns the next 2 results from the 5-row set."""
    for i in range(5):
        db_session.add(_make_ai_cve(strike_name=f"Paged-{i}"))
    await db_session.commit()

    page1 = await test_client.get("/ai-cves?page=1&limit=2")
    page2 = await test_client.get("/ai-cves?page=2&limit=2")

    assert page1.status_code == 200
    assert page2.status_code == 200

    names_page1 = {r["ai_strike_name"] for r in page1.json()["results"]}
    names_page2 = {r["ai_strike_name"] for r in page2.json()["results"]}

    # No overlap between pages
    assert names_page1.isdisjoint(names_page2)
    # Each page has exactly 2 results
    assert len(names_page1) == 2
    assert len(names_page2) == 2
    # Total is consistent across pages
    assert page1.json()["total"] == 5
    assert page2.json()["total"] == 5


# ─── Test 4: Filter by strike_type ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_ai_cves_filter_by_strike_type(test_client, db_session):
    """strike_type=fuzzing returns only fuzzing rows; ai_attack rows excluded."""
    db_session.add(_make_ai_cve(strike_name="AI-Strike-1", strike_type="ai_attack"))
    db_session.add(_make_ai_cve(strike_name="AI-Strike-2", strike_type="ai_attack"))
    db_session.add(_make_ai_cve(strike_name="Fuzz-Strike-1", strike_type="fuzzing"))
    await db_session.commit()

    response = await test_client.get("/ai-cves?strike_type=fuzzing")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["ai_strike_name"] == "Fuzz-Strike-1"


@pytest.mark.asyncio
async def test_list_ai_cves_filter_no_matches_returns_empty(test_client, db_session):
    """strike_type filter with no matching rows returns empty results, not 404."""
    db_session.add(_make_ai_cve(strike_name="Only-AI", strike_type="ai_attack"))
    await db_session.commit()

    response = await test_client.get("/ai-cves?strike_type=protocol_abuse")
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []
    assert body["total"] == 0


# ─── Test 5: Response shape ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_ai_cves_response_shape(test_client, db_session):
    """Every result row has the exact keys defined by AiCVEResponse schema."""
    db_session.add(_make_ai_cve(strike_name="Shape-Check-Strike"))
    await db_session.commit()

    response = await test_client.get("/ai-cves")
    assert response.status_code == 200
    body = response.json()

    assert "results" in body
    assert "total" in body

    assert len(body["results"]) >= 1
    row = body["results"][0]

    expected_keys = {
        "id",
        "description",
        "severity",
        "cvss_score",
        "ai_strike_name",
        "generated_at",
    }
    assert (
        set(row.keys()) == expected_keys
    ), f"Response shape mismatch. Got: {set(row.keys())} Expected: {expected_keys}"

    # Null fields that are not stored in ai_cves
    assert row["description"] is None
    assert row["severity"] is None
    assert row["cvss_score"] is None

    # Non-null fields that are stored
    assert row["id"] is not None
    assert isinstance(row["id"], str)
    assert row["id"].startswith("NoCVE_cyperf")
    assert row["ai_strike_name"] == "Shape-Check-Strike"
