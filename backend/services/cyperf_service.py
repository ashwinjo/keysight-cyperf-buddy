"""Cyperf API integration service.

Uses the official cyperf-api-wrapper Python client (ApplicationResourcesApi)
to fetch Strike data and extract CVE→Strike mappings via paginated batching.

No direct HTTP calls — all Cyperf communication goes through cyperf.ApiClient.
"""

import json
import logging
import uuid
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


@dataclass
class AIStrikeRecord:
    """A single Cyperf strike that has no Type='CVE' reference.

    Attributes:
        row_id: uuid4 surrogate PK for this insert cycle (changes each full-replace).
        cve_id: Deterministic NoCVE_cyperf<uuid5(NAMESPACE_DNS, strike_name)> synthetic ID.
        strike_name: Full Cyperf strike name from the API response.
        strike_type: Category tag; default 'ai_attack'.
        metadata_json: json.dumps() of raw Metadata.References list, or None if empty.
    """

    row_id: str
    cve_id: str
    strike_name: str
    strike_type: str
    metadata_json: str | None


@dataclass
class StrikeFetchResult:
    """Combined result of fetch_cve_strike_mappings().

    Attributes:
        cve_mappings: CVE-YYYY-NNNNN -> strike_name dict for strikes with real CVE refs.
        ai_strikes: List of AIStrikeRecord for strikes with no Type='CVE' reference.
    """

    cve_mappings: dict[str, str]
    ai_strikes: list[AIStrikeRecord]


# Namespace for uuid5-based synthetic CVE ID generation.
# Using NAMESPACE_DNS (the standard DNS namespace) as the stable seed.
CYPERF_AI_NAMESPACE = uuid.NAMESPACE_DNS


def _make_synthetic_cve_id(strike_name: str) -> str:
    """Generate a deterministic NoCVE_cyperf<uuid5> identifier for a no-CVE strike.

    Uses uuid5(NAMESPACE_DNS, strike_name) so the same strike_name always
    produces the same cve_id across re-syncs, making full-replace idempotent
    for any downstream system that bookmarks the synthetic ID.

    Args:
        strike_name: Full Cyperf strike name from the API response.

    Returns:
        String in the form 'NoCVE_cyperf<uuid5-hex>' (49 chars total).
    """
    deterministic = uuid.uuid5(CYPERF_AI_NAMESPACE, strike_name)
    return f"NoCVE_cyperf{deterministic}"


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

    async def fetch_cve_strike_mappings(self) -> StrikeFetchResult:
        """Fetch all CVE→Strike mappings and AI-type strikes from Cyperf.

        Uses ApplicationResourcesApi.get_resources_strikes() with skip/take=500 batching.
        Extracts CVE IDs from strike.get("Metadata", {}).get("References", [])
        where Type="CVE". Strikes that complete the references loop with no
        Type='CVE' reference found are classified as AI-type strikes and
        recorded in the ai_strikes list with a synthetic NoCVE_cyperf<uuid5> ID.

        Returns:
            StrikeFetchResult with:
              - cve_mappings: dict of CVE ID (e.g. "CVE-2024-1234") -> Strike name.
                When one CVE maps to multiple strikes, the last strike processed wins.
              - ai_strikes: list of AIStrikeRecord for no-CVE strikes (AI attacks,
                protocol fuzzing, etc.) with synthetic deterministic IDs.

        Raises:
            CyperfConnectionError: If connection to controller fails or times out
            CyperfAPIError: If API returns 401/403 or another unexpected HTTP error
        """
        cve_mappings: dict[str, str] = {}
        ai_strikes: list[AIStrikeRecord] = []
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
                        found_cve = False

                        for ref in refs:
                            if ref.get("Type") == "CVE" and ref.get("Value"):
                                cve_id = f"CVE-{ref['Value']}"
                                cve_mappings[cve_id] = strike_name
                                found_cve = True
                            elif ref.get("Type") == "CVE":
                                logger.warning(
                                    f"Incomplete CVE reference in strike '{strike_name}': {ref}"
                                )

                        if not found_cve:
                            # No Type='CVE' reference found after iterating all refs.
                            # Treat as AI/no-CVE strike and assign a synthetic ID.
                            synthetic_cve_id = _make_synthetic_cve_id(strike_name)
                            ai_strikes.append(
                                AIStrikeRecord(
                                    row_id=str(uuid.uuid4()),
                                    cve_id=synthetic_cve_id,
                                    strike_name=strike_name,
                                    strike_type="ai_attack",
                                    metadata_json=json.dumps(refs) if refs else None,
                                )
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

        logger.info(
            f"Fetched {profiles_count} strikes, {len(cve_mappings)} CVE mappings, "
            f"{len(ai_strikes)} AI strikes"
        )
        return StrikeFetchResult(cve_mappings=cve_mappings, ai_strikes=ai_strikes)

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
            fetch_result: StrikeFetchResult = await self.fetch_cve_strike_mappings()
            return SyncResult(
                profiles_fetched=0,
                cves_extracted=len(fetch_result.cve_mappings),
                error=None,
            )
        except (CyperfConnectionError, CyperfAPIError) as e:
            logger.error(f"Sync failed: {e}")
            return SyncResult(profiles_fetched=0, cves_extracted=0, error=str(e))
        except Exception as e:
            logger.error(f"Unexpected sync error: {type(e).__name__}: {e}")
            return SyncResult(profiles_fetched=0, cves_extracted=0, error=f"Unexpected: {e}")
