"""Cyperf API integration service.

Uses the official cyperf-api-wrapper Python client (ApplicationResourcesApi)
to fetch Strike data and extract CVE→Strike mappings via paginated batching.

No direct HTTP calls for sync — all Cyperf communication goes through cyperf.ApiClient.
Connectivity validation for the admin config endpoint uses httpx with a 5-second timeout.
"""

import asyncio
import json
import logging
import socket
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


async def validate_endpoint_connectivity(endpoint: str) -> tuple[bool, str]:
    """Check whether a Keysight CyPerf Controller endpoint is reachable.

    Attempts a GET request to ``https://{endpoint}/api/v2/profiles`` with a
    5-second timeout.  SSL certificate errors are treated as a reachable-but-
    misconfigured signal (returns True) because CyPerf ships with a self-signed
    certificate by default.

    The function never raises — all failures are captured and returned as
    ``(False, human_readable_error_message)``.

    Args:
        endpoint: Hostname or IP of the CyPerf Controller, without protocol prefix.
                  Example: ``"cyperf.example.com"`` or ``"192.168.1.100"``.

    Returns:
        Tuple of:
            - ``is_valid`` (bool): True if the endpoint is reachable.
            - ``error_message`` (str): Empty string on success; human-readable
              reason on failure.
    """
    try:
        import httpx
    except ImportError:
        logger.error("httpx is not installed — cannot validate endpoint connectivity")
        return False, "Server configuration error: httpx library not available"

    url = f"https://{endpoint}/api/v2/profiles"
    logger.info("Validating CyPerf endpoint connectivity: %s", url)

    try:
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:  # noqa: S501
            response = await client.get(url)

        # Any HTTP response (200, 401, 403, 404, 500) means the host is reachable
        logger.info("CyPerf endpoint %s responded with HTTP %d", endpoint, response.status_code)
        return True, ""

    except httpx.ConnectTimeout:
        msg = "Endpoint unreachable (connection timeout after 5 seconds)"
        logger.warning("Connectivity check timed out for %s", endpoint)
        return False, msg

    except httpx.ReadTimeout:
        msg = "Endpoint unreachable (read timeout after 5 seconds)"
        logger.warning("Connectivity check read-timeout for %s", endpoint)
        return False, msg

    except httpx.ConnectError as exc:
        # Covers refused connections and DNS resolution failures
        err_lower = str(exc).lower()
        if "name or service not known" in err_lower or "nodename nor servname" in err_lower:
            msg = f"DNS resolution failed for endpoint '{endpoint}'"
        elif "connection refused" in err_lower:
            msg = f"Connection refused by endpoint '{endpoint}'"
        else:
            msg = f"Cannot connect to endpoint '{endpoint}': {exc}"
        logger.warning("Connectivity check connect-error for %s: %s", endpoint, exc)
        return False, msg

    except socket.gaierror:
        msg = f"DNS resolution failed for endpoint '{endpoint}'"
        logger.warning("DNS resolution failed for %s", endpoint)
        return False, msg

    except Exception as exc:
        msg = f"Unexpected error validating endpoint '{endpoint}': {type(exc).__name__}"
        logger.error("Unexpected connectivity check error for %s: %s", endpoint, exc)
        return False, msg


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

        The cyperf-api-wrapper client is synchronous (urllib3-based). Dispatching
        to a thread via asyncio.to_thread() keeps the uvicorn event loop free to
        serve health checks and API requests while the blocking I/O runs.

        Raises:
            CyperfConnectionError: If connection to controller fails or times out
            CyperfAPIError: If API returns 401/403 or another unexpected HTTP error
        """
        return await asyncio.to_thread(self._fetch_cve_strike_mappings_sync)

    def _fetch_cve_strike_mappings_sync(self) -> StrikeFetchResult:
        """Blocking implementation — runs in a thread pool via asyncio.to_thread().

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
