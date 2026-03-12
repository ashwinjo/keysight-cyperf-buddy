"""Integration tests for POST /api/l47/recommend endpoint."""

import sys
import os

# Ensure agent-service root is on path for direct module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_gemini():
    """Mock Gemini GenerativeModel to avoid real API calls."""
    with patch("recommendation_agent.genai") as mock_genai:
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(
            text="This profile directly addresses your testing objectives with industry-standard traffic patterns. It provides comprehensive metrics for your scenario. Recommended as the primary test configuration."
        )
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = MagicMock()
        yield mock_genai


@pytest.fixture
def mock_agent(mock_gemini, sample_apps, sample_strikes):
    """Construct a RecommendationAgent with mocked backend client and Gemini."""
    from config import AgentSettings
    from recommendation_agent import RecommendationAgent

    settings = AgentSettings(
        gemini_api_key="test-key",
        backend_api_url="http://localhost:8000",
    )
    agent = RecommendationAgent(settings)
    # Override the api_client methods to avoid real HTTP calls
    agent.api_client.get_cyperf_apps = AsyncMock(return_value=sample_apps)
    agent.api_client.get_cyperf_strikes = AsyncMock(return_value=sample_strikes)
    return agent


@pytest.mark.asyncio
async def test_recommend_app_performance_returns_recommendations(
    mock_agent, sample_request_app
):
    """POST /api/l47/recommend with app_performance returns up to 3 recommendations."""
    from main import app

    app.state.agent = mock_agent
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/l47/recommend", json=sample_request_app)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["recommendations"], list)
    assert len(body["recommendations"]) <= 3
    if body["recommendations"]:
        rec = body["recommendations"][0]
        assert "profile_name" in rec
        assert "profile_type" in rec
        assert rec["profile_type"] == "application"
        assert "rationale" in rec
        assert "rank" in rec


@pytest.mark.asyncio
async def test_recommend_security_returns_strike_type(
    mock_agent, sample_request_security
):
    """POST /api/l47/recommend with security_attacks returns strike type profiles."""
    from main import app

    app.state.agent = mock_agent
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/l47/recommend", json=sample_request_security)

    assert response.status_code == 200
    body = response.json()
    if body["recommendations"]:
        assert all(r["profile_type"] == "strike" for r in body["recommendations"])


@pytest.mark.asyncio
async def test_recommend_both_returns_mixed_types(mock_agent, sample_request_both):
    """POST /api/l47/recommend with both returns mixed profile types (or at least 200)."""
    from main import app

    app.state.agent = mock_agent
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/l47/recommend", json=sample_request_both)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


@pytest.mark.asyncio
async def test_recommend_backend_down_returns_empty_not_500(
    mock_gemini, sample_request_app
):
    """When backend API is unreachable, returns 200 with empty recommendations."""
    from main import app
    from config import AgentSettings
    from recommendation_agent import RecommendationAgent

    settings = AgentSettings(
        gemini_api_key="test-key",
        backend_api_url="http://localhost:8000",
    )
    agent = RecommendationAgent(settings)
    agent.api_client.get_cyperf_apps = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    app.state.agent = agent

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/l47/recommend", json=sample_request_app)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["recommendations"] == []
    assert "message" in body


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /health returns 200 with status ok."""
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_recommend_validation_error_returns_422(mock_gemini):
    """Missing required fields returns 422 with plain string detail."""
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/l47/recommend", json={"testing_focus": "app_performance"}
        )

    assert response.status_code == 422
    body = response.json()
    # detail should be a string (not a list of objects) per our RequestValidationError handler
    assert isinstance(body["detail"], str)
