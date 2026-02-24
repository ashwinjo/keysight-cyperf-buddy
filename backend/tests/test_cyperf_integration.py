"""Integration tests for Cyperf sync functionality.

This module provides comprehensive tests for:
- CyperfService API client (ApplicationResourcesApi pattern)
- CVE extraction logic from Strike References
- Sync orchestration with retry logic and graceful degradation
"""

import json
import os
from typing import Any
from unittest.mock import MagicMock, patch

import asyncpg
import pytest
from sqlalchemy import select

from config import Settings
from database import AsyncSessionLocal, engine
from db.cverf_cve_strike_mappings import CvrfCveStrikeMappings
from db.sync_metadata import SyncMetadata
from services.cyperf_service import (
    CyperfAPIError,
    CyperfConnectionError,
    CyperfService,
)
from services.sync_service import perform_sync

# ============================================================================
# Helpers
# ============================================================================

# Use the environment DATABASE_URL directly (not Settings which test conftest overrides)
# This ensures we connect to the live PostgreSQL DB, not the in-memory SQLite test DB.
_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://cyperf_dev:cyperf_dev_password@postgres:5432/cyperf_cve_dev",
).replace("postgresql+asyncpg://", "postgresql://")


async def _clean_cverf_rows() -> None:
    """Delete all rows from cverf_cve_strike_mappings and sync_metadata.

    Disposes the SQLAlchemy connection pool first to release all checked-out
    asyncpg connections, then connects directly via asyncpg for clean deletion.
    This avoids 'another operation is in progress' pool conflicts between tests.
    """
    # Release all SQLAlchemy pool connections before getting a raw asyncpg connection
    await engine.dispose()
    conn = await asyncpg.connect(_DB_URL)
    try:
        await conn.execute("DELETE FROM cverf_cve_strike_mappings")
        await conn.execute("DELETE FROM sync_metadata")
    finally:
        await conn.close()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with mock Cyperf controller."""
    return Settings(
        cyperf_controller_ip="52.32.20.150",
        cyperf_username="admin",
        cyperf_password="test_password",
        cyperf_sync_interval_hours=24,
        database_url="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
def mock_strikes() -> list[dict[str, Any]]:
    """Mock Strike data matching cyperf-api-wrapper get_resources_strikes() response format.

    Covers: normal strikes with CVE refs, strike without CVE refs, malformed strike.
    """
    return [
        {
            "Name": "Apache-Log4j-RCE",
            "Metadata": {
                "References": [
                    {"Type": "CVE", "Value": "2021-44228"},
                    {"Type": "CVE", "Value": "2021-44229"},
                ],
            },
        },
        {
            "Name": "Microsoft-Exchange-ProxyLogon",
            "Metadata": {
                "References": [
                    {"Type": "CVE", "Value": "2021-26855"},
                    {"Type": "CVE", "Value": "2021-26857"},
                ],
            },
        },
        {
            "Name": "No-CVE-Strike",
            "Metadata": {
                "References": [
                    {"Type": "OTHER", "Value": "some-other-ref"},
                ],
            },
        },
        {
            "Name": "Malformed-Strike",
            # Missing Metadata entirely -- service must log warning and skip
        },
    ]


# ============================================================================
# Unit Tests: CyperfService fetch_cve_strike_mappings
# ============================================================================


class TestCyperfServiceFetchMappings:
    """Test CyperfService.fetch_cve_strike_mappings() using ApplicationResourcesApi pattern."""

    def _make_page_response(self, strikes: list[dict]) -> MagicMock:
        """Build a mock API response that returns strikes via to_json()."""
        mock_response = MagicMock()
        mock_response.to_json.return_value = json.dumps({"data": strikes})
        return mock_response

    def _make_empty_response(self) -> MagicMock:
        """Build a mock API response with no strikes (signals end of pagination)."""
        mock_response = MagicMock()
        mock_response.to_json.return_value = json.dumps({"data": []})
        return mock_response

    @pytest.mark.asyncio
    async def test_fetch_mappings_extracts_cves_correctly(self, test_settings, mock_strikes):
        """CVE IDs have CVE- prefix prepended: Value='2021-44228' -> 'CVE-2021-44228'."""
        page1_response = self._make_page_response(mock_strikes)
        empty_response = self._make_empty_response()

        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = [
                page1_response,
                empty_response,
            ]

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )
            result = await service.fetch_cve_strike_mappings()

        # Verify CVE ID prefixing
        assert "CVE-2021-44228" in result
        assert "CVE-2021-44229" in result
        assert "CVE-2021-26855" in result
        assert "CVE-2021-26857" in result

        # Verify Strike names are values
        assert result["CVE-2021-44228"] == "Apache-Log4j-RCE"
        assert result["CVE-2021-26855"] == "Microsoft-Exchange-ProxyLogon"

    @pytest.mark.asyncio
    async def test_fetch_mappings_skips_non_cve_references(self, test_settings, mock_strikes):
        """References with Type != 'CVE' are excluded from the result."""
        page1_response = self._make_page_response(mock_strikes)
        empty_response = self._make_empty_response()

        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = [
                page1_response,
                empty_response,
            ]

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )
            result = await service.fetch_cve_strike_mappings()

        # No-CVE-Strike has only Type=OTHER references -- must not appear in result values
        assert "No-CVE-Strike" not in result.values()

    @pytest.mark.asyncio
    async def test_fetch_mappings_skips_malformed_strikes(self, test_settings, mock_strikes):
        """Strike with missing Metadata is skipped (warning logged), not an exception."""
        page1_response = self._make_page_response(mock_strikes)
        empty_response = self._make_empty_response()

        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = [
                page1_response,
                empty_response,
            ]

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )
            # Should not raise even with malformed Malformed-Strike in the batch
            result = await service.fetch_cve_strike_mappings()

        # Malformed-Strike has no Metadata; must not appear in result values
        assert "Malformed-Strike" not in result.values()
        # Valid CVEs from other strikes must still be present
        assert "CVE-2021-44228" in result

    @pytest.mark.asyncio
    async def test_fetch_mappings_paginates_correctly(self, test_settings):
        """Pagination: first call returns strikes, second call returns empty (stop signal)."""
        page1_strikes = [
            {
                "Name": "Strike-A",
                "Metadata": {"References": [{"Type": "CVE", "Value": "2024-0001"}]},
            },
        ]
        page1_response = MagicMock()
        page1_response.to_json.return_value = json.dumps({"data": page1_strikes})
        empty_response = MagicMock()
        empty_response.to_json.return_value = json.dumps({"data": []})

        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = [
                page1_response,
                empty_response,
            ]

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )
            result = await service.fetch_cve_strike_mappings()

        assert "CVE-2024-0001" in result
        assert result["CVE-2024-0001"] == "Strike-A"
        # Should have called get_resources_strikes exactly twice (page1 + empty terminator)
        assert mock_api_instance.get_resources_strikes.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_mappings_handles_connection_error(self, test_settings):
        """ConnectionError from API raises CyperfConnectionError."""
        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = ConnectionError(
                "Connection refused"
            )

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )

            with pytest.raises(CyperfConnectionError):
                await service.fetch_cve_strike_mappings()

    @pytest.mark.asyncio
    async def test_fetch_mappings_handles_auth_error(self, test_settings):
        """Exception with '401 Unauthorized' raises CyperfAPIError with 'Authentication failed'."""
        with patch("services.cyperf_service.cyperf") as mock_cyperf:
            mock_api_client = MagicMock()
            mock_api_instance = MagicMock()
            mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
            mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
            mock_api_instance.get_resources_strikes.side_effect = Exception("401 Unauthorized")

            service = CyperfService(
                controller_ip=test_settings.cyperf_controller_ip,
                username=test_settings.cyperf_username,
                password=test_settings.cyperf_password,
            )

            with pytest.raises(CyperfAPIError) as exc_info:
                await service.fetch_cve_strike_mappings()

            assert "Authentication failed" in str(exc_info.value)


# ============================================================================
# Integration Tests: Sync Service (new cverf_cve_strike_mappings schema)
# ============================================================================


class TestPerformSyncRefactored:
    """Test perform_sync() against the new cverf_cve_strike_mappings table.

    Uses the live PostgreSQL DB (AsyncSessionLocal).
    Each test performs setup/teardown via raw asyncpg to bypass SQLAlchemy pool state.
    """

    def _page(self, strikes: list[dict]) -> MagicMock:
        r = MagicMock()
        r.to_json.return_value = json.dumps({"data": strikes})
        return r

    def _empty_page(self) -> MagicMock:
        r = MagicMock()
        r.to_json.return_value = json.dumps({"data": []})
        return r

    def _patch_cyperf(self, strikes_side_effect):
        """Return context manager patching cyperf module with given side_effect."""
        mock_cyperf = MagicMock()
        mock_api_client = MagicMock()
        mock_api_instance = MagicMock()
        mock_cyperf.ApiClient.return_value.__enter__ = MagicMock(return_value=mock_api_client)
        mock_cyperf.ApiClient.return_value.__exit__ = MagicMock(return_value=False)
        mock_cyperf.ApplicationResourcesApi.return_value = mock_api_instance
        mock_api_instance.get_resources_strikes.side_effect = strikes_side_effect
        return patch("services.cyperf_service.cyperf", mock_cyperf)

    @pytest.mark.asyncio
    async def test_perform_sync_full_replace_removes_old_data(self, test_settings):
        """Full-replace: old cverf_cve_strike_mappings rows are gone after successful sync."""
        await _clean_cverf_rows()

        async with AsyncSessionLocal() as session:
            session.add(CvrfCveStrikeMappings(cve_id="CVE-2020-0001", strike_name="Old-Strike"))
            await session.commit()

            with self._patch_cyperf(
                [
                    self._page(
                        [
                            {
                                "Name": "New-Strike",
                                "Metadata": {"References": [{"Type": "CVE", "Value": "2024-9999"}]},
                            }
                        ]
                    ),
                    self._empty_page(),
                ]
            ):
                await perform_sync(session, test_settings)

            result = await session.execute(select(CvrfCveStrikeMappings))
            rows = result.scalars().all()

        cve_ids = {r.cve_id for r in rows}
        assert "CVE-2020-0001" not in cve_ids, "Old row must be replaced by full-replace sync"
        assert "CVE-2024-9999" in cve_ids, "New row must be inserted by sync"

        await _clean_cverf_rows()

    @pytest.mark.asyncio
    async def test_perform_sync_failure_retains_old_cverf_mappings(self, test_settings):
        """On sync failure, existing cverf_cve_strike_mappings rows are retained."""
        await _clean_cverf_rows()

        async with AsyncSessionLocal() as session:
            session.add(CvrfCveStrikeMappings(cve_id="CVE-2021-1111", strike_name="Stable-Strike"))
            await session.commit()

            with self._patch_cyperf(ConnectionError("Controller unreachable")):
                await perform_sync(session, test_settings)

            result = await session.execute(select(CvrfCveStrikeMappings))
            rows = result.scalars().all()
            cve_ids = {r.cve_id for r in rows}
            assert "CVE-2021-1111" in cve_ids, "Existing rows must survive a failed sync"

            metadata = await SyncMetadata.get_last_sync_status(session, job_name="cyperf_profiles")
            assert metadata is not None
            assert metadata.status == "failed"

        await _clean_cverf_rows()

    @pytest.mark.asyncio
    async def test_perform_sync_records_metadata_on_success(self, test_settings):
        """Successful sync records SyncMetadata with status='success'."""
        await _clean_cverf_rows()

        async with AsyncSessionLocal() as session:
            with self._patch_cyperf(
                [
                    self._page(
                        [
                            {
                                "Name": "Success-Strike",
                                "Metadata": {"References": [{"Type": "CVE", "Value": "2024-1234"}]},
                            }
                        ]
                    ),
                    self._empty_page(),
                ]
            ):
                await perform_sync(session, test_settings)

            metadata = await SyncMetadata.get_last_sync_status(session, job_name="cyperf_profiles")
            assert metadata is not None
            assert metadata.status == "success"

        await _clean_cverf_rows()

    @pytest.mark.asyncio
    async def test_perform_sync_writes_json_artifact(self, test_settings, tmp_path):
        """Successful sync writes cve_strikes.json artifact with correct format."""
        await _clean_cverf_rows()

        json_path = str(tmp_path / "cve_strikes.json")
        test_settings_with_path = Settings(
            cyperf_controller_ip=test_settings.cyperf_controller_ip,
            cyperf_username=test_settings.cyperf_username,
            cyperf_password=test_settings.cyperf_password,
            cyperf_sync_interval_hours=test_settings.cyperf_sync_interval_hours,
            database_url=test_settings.database_url,
            cve_strikes_output_path=json_path,
        )

        async with AsyncSessionLocal() as session:
            with self._patch_cyperf(
                [
                    self._page(
                        [
                            {
                                "Name": "Json-Strike",
                                "Metadata": {
                                    "References": [
                                        {"Type": "CVE", "Value": "2024-5555"},
                                        {"Type": "CVE", "Value": "2024-6666"},
                                    ]
                                },
                            }
                        ]
                    ),
                    self._empty_page(),
                ]
            ):
                await perform_sync(session, test_settings_with_path)

        assert os.path.exists(json_path), "JSON artifact must be created after successful sync"

        with open(json_path) as f:
            artifact = json.load(f)

        assert isinstance(artifact, dict)
        assert "CVE-2024-5555" in artifact
        assert "CVE-2024-6666" in artifact
        assert artifact["CVE-2024-5555"] == "Json-Strike"

        await _clean_cverf_rows()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Run tests with pytest
    # pytest backend/tests/test_cyperf_integration.py -v
    pytest.main([__file__, "-v"])
