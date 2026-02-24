"""Shared test fixtures for Phase 2 integration tests."""

import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Set required env vars before any imports that trigger Settings validation
os.environ.setdefault("CYPERF_CONTROLLER_IP", "test-host")
os.environ.setdefault("CYPERF_USERNAME", "test-user")
os.environ.setdefault("CYPERF_PASSWORD", "test-password")
os.environ.setdefault("SMTP_USERNAME", "test@keysight.com")
os.environ.setdefault("SMTP_PASSWORD", "test-password")

from database import Base, get_db  # noqa: E402
from dependencies import get_cache_service, get_nvd_client  # noqa: E402
from main import app  # noqa: E402
from services.cache_service import CVECacheService  # noqa: E402
from services.nvd_service import NVDClient  # noqa: E402

# ─── Sample CVE data fixture ───────────────────────────────────────────────


@pytest.fixture
def sample_cve_dict() -> dict:
    """Minimal valid CVE dict matching application schema."""
    return {
        "id": "CVE-2024-1234",
        "description": "A critical remote code execution vulnerability.",
        "published_date": "2024-01-15T10:00:00",
        "cvss_v3_score": 9.8,
        "cvss_v3_severity": "CRITICAL",
        "cvss_v3_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "cvss_v4_score": None,
        "cvss_v4_severity": None,
        "cvss_v4_vector": None,
        "reference_urls": ["https://example.com/advisory"],
        "testable": None,
    }


# ─── DB Fixture (SQLite in-memory) ─────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSession() as session:
        yield session

    await engine.dispose()


# ─── Mock NVD Client ────────────────────────────────────────────────────────


@pytest.fixture
def mock_nvd_client(sample_cve_dict: dict) -> NVDClient:
    """Mock NVDClient that returns sample CVE data without hitting NVD API."""
    mock_cve_obj = MagicMock()
    mock_cve_obj.id = sample_cve_dict["id"]
    mock_cve_obj.published = sample_cve_dict["published_date"]
    mock_cve_obj.descriptions = [MagicMock(lang="en", value=sample_cve_dict["description"])]
    mock_cve_obj.references = [MagicMock(url=u) for u in sample_cve_dict["reference_urls"]]
    mock_cve_obj.v31score = sample_cve_dict["cvss_v3_score"]
    mock_cve_obj.v31severity = sample_cve_dict["cvss_v3_severity"]
    mock_cve_obj.v31vector = sample_cve_dict["cvss_v3_vector"]
    mock_cve_obj.v40score = None
    mock_cve_obj.v40severity = None
    mock_cve_obj.v40vector = None

    client = AsyncMock(spec=NVDClient)
    client.fetch_cve.return_value = mock_cve_obj
    client.fetch_latest.return_value = [mock_cve_obj]
    return client


# ─── Mock Redis / Cache Service ─────────────────────────────────────────────


@pytest.fixture
def mock_cache_service() -> CVECacheService:
    """Mock CVECacheService with in-memory dict store."""
    store: dict = {}
    ttl_store: dict = {}

    svc = AsyncMock(spec=CVECacheService)

    async def mock_get(cve_id: str):
        return store.get(cve_id.upper())

    async def mock_set(cve_id: str, data: dict):
        store[cve_id.upper()] = data
        ttl_store[cve_id.upper()] = 86400
        return True

    async def mock_get_remaining_ttl(cve_id: str):
        return ttl_store.get(cve_id.upper(), -2)

    async def mock_exists(cve_id: str):
        return cve_id.upper() in store

    def mock_is_stale(remaining_ttl: int) -> bool:
        """True if remaining TTL < 4h (STALE_REFRESH_THRESHOLD_SECONDS = 14400)."""
        return 0 <= remaining_ttl < 14400

    svc.get.side_effect = mock_get
    svc.set.side_effect = mock_set
    svc.get_remaining_ttl.side_effect = mock_get_remaining_ttl
    svc.exists.side_effect = mock_exists
    svc.is_stale.side_effect = mock_is_stale

    # Expose store for tests to pre-populate the cache
    svc._store = store
    svc._ttl_store = ttl_store

    return svc


# ─── Test client with dependency overrides ──────────────────────────────────


@pytest_asyncio.fixture
async def test_client(
    mock_nvd_client: NVDClient,
    mock_cache_service: CVECacheService,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with mocked NVD, cache, and in-memory DB."""
    app.dependency_overrides[get_nvd_client] = lambda: mock_nvd_client
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service
    app.dependency_overrides[get_db] = lambda: db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
