"""Cyperf API integration service.

Uses the official cyperf-api-wrapper Python client (ApplicationResourcesApi)
to fetch Strike data and extract CVE→Strike mappings via paginated batching.

No direct HTTP calls — all Cyperf communication goes through cyperf.ApiClient.
"""

import json
import logging
from dataclasses import dataclass

try:
    import cyperf
except ImportError as _import_err:
    raise ImportError(
        "cyperf-api-wrapper not installed; run: pip install cyperf-api-wrapper"
    ) from _import_err

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


@dataclass
class SyncResult:
    """Result of a Cyperf sync operation."""

    profiles_fetched: int
    cves_extracted: int
    error: str | None = None


class CyperfConnectionError(Exception):
    """Raised when connection to Cyperf Controller fails."""

    pass


class CyperfAPIError(Exception):
    """Raised when Cyperf API returns an error (auth/permission/HTTP failures)."""

    pass


class CyperfService:
    """Service for integrating with Cyperf Controller via cyperf-api-wrapper.

    All API communication uses the official Keysight Python client
    (ApplicationResourcesApi). No direct httpx calls are made.
    """

    def __init__(self, controller_ip: str, username: str, password: str) -> None:
        """Initialize Cyperf service with API wrapper configuration.

        Args:
            controller_ip: IP address or hostname of the Cyperf Controller
            username: Cyperf Controller username
            password: Cyperf Controller password

        Note:
            Does NOT open a network connection at construction time.
            Connection is established per-call via ApiClient context manager.
            verify_ssl=False is required for Cyperf's self-signed certificates.
        """
        self.controller_ip = controller_ip

        self._config = cyperf.Configuration(
            host=f"https://{controller_ip}",
            username=username,
            password=password,
        )
        self._config.verify_ssl = False

        logger.info(f"Initialized CyperfService for {controller_ip}")

    async def fetch_cve_strike_mappings(self) -> dict[str, str]:
        """Fetch all CVE→Strike mappings from Cyperf using paginated API calls.

        Uses ApplicationResourcesApi.get_resources_strikes() with skip/take=500 batching.
        Extracts CVE IDs from strike.get("Metadata", {}).get("References", [])
        where Type="CVE".

        Returns:
            dict mapping CVE ID (e.g. "CVE-2024-1234") to Strike name
            (e.g. "Apache-Log4j-RCE"). When one CVE maps to multiple strikes,
            the last strike processed wins (single-value JSON map structure).

        Raises:
            CyperfConnectionError: If connection to controller fails or times out
            CyperfAPIError: If API returns 401/403 or another unexpected HTTP error
        """
        cve_mappings: dict[str, str] = {}
        profiles_count = 0
        skip = 0

        try:
            with cyperf.ApiClient(self._config) as api_client:
                api_instance = cyperf.ApplicationResourcesApi(api_client)

                while True:
                    response = api_instance.get_resources_strikes(take=BATCH_SIZE, skip=skip)
                    strikes = json.loads(response.to_json()).get("data", [])

                    if not strikes:
                        break

                    for strike in strikes:
                        strike_name = strike.get("Name", "Unknown")
                        refs = strike.get("Metadata", {}).get("References", [])
                        for ref in refs:
                            if ref.get("Type") == "CVE" and ref.get("Value"):
                                cve_id = f"CVE-{ref['Value']}"
                                cve_mappings[cve_id] = strike_name
                            elif ref.get("Type") == "CVE":
                                logger.warning(
                                    f"Incomplete CVE reference in strike '{strike_name}': {ref}"
                                )

                    profiles_count += len(strikes)
                    logger.info(f"Processed batch skip={skip}: {len(strikes)} strikes")
                    skip += BATCH_SIZE

        except (CyperfConnectionError, CyperfAPIError):
            raise
        except Exception as e:
            err_lower = str(e).lower()
            if "401" in err_lower or "unauthorized" in err_lower:
                raise CyperfAPIError(f"Authentication failed: {e}") from e
            if "403" in err_lower or "forbidden" in err_lower:
                raise CyperfAPIError(f"Permission denied: {e}") from e
            if "connect" in err_lower or "timeout" in err_lower or "refused" in err_lower:
                raise CyperfConnectionError(
                    f"Cannot connect to Cyperf at {self.controller_ip}: {e}"
                ) from e
            raise CyperfConnectionError(f"Unexpected error from Cyperf API: {e}") from e

        logger.info(f"Fetched {profiles_count} strikes, extracted {len(cve_mappings)} CVE mappings")
        return cve_mappings

    async def sync_cyperf_cves(self, retry_count: int = 0) -> SyncResult:
        """Orchestrate CVE sync via fetch_cve_strike_mappings().

        Exists for backward compatibility with existing scheduler call-sites.
        The primary data path in Phase 3.1 is sync_service.py calling
        fetch_cve_strike_mappings() directly.

        Args:
            retry_count: Unused; kept for backward-compatible signature

        Returns:
            SyncResult with cves_extracted count; profiles_fetched is 0
            (not tracked separately — absorbed into cves_extracted).
            On error, returns SyncResult with error message set.
        """
        try:
            cve_mappings = await self.fetch_cve_strike_mappings()
            return SyncResult(
                profiles_fetched=0,
                cves_extracted=len(cve_mappings),
                error=None,
            )
        except (CyperfConnectionError, CyperfAPIError) as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(profiles_fetched=0, cves_extracted=0, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected sync error: {type(e).__name__}: {e}")
            return SyncResult(profiles_fetched=0, cves_extracted=0, error=f"Unexpected: {e}")
