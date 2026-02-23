"""Cyperf API integration service."""

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


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
    """Raised when Cyperf API returns an error."""

    pass


class CyperfService:
    """Service for integrating with Cyperf Controller via cyperf-api-wrapper."""

    def __init__(self, controller_ip: str, username: str, password: str) -> None:
        """Initialize Cyperf API client.

        Args:
            controller_ip: IP address of Cyperf Controller
            username: Username for authentication
            password: Password for authentication

        Raises:
            CyperfConnectionError: If unable to connect to controller
        """
        self.controller_ip = controller_ip
        self.username = username
        self.password = password
        self.client = None

        # Import cyperf-api-wrapper at initialization time
        try:
            from cyperf_api_wrapper import CyperfApiClient  # type: ignore[import-not-found]

            logger.info(f"Initializing Cyperf API client for controller {controller_ip}")
            self.client = CyperfApiClient(
                controller_address=controller_ip,
                username=username,
                password=password,
            )
            logger.info(f"✓ Cyperf API client initialized for {controller_ip}")
        except ImportError as e:
            logger.error("cyperf-api-wrapper not installed; unable to initialize Cyperf service")
            raise CyperfConnectionError(f"cyperf-api-wrapper import failed: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize Cyperf API client: {e}")
            raise CyperfConnectionError(
                f"Unable to connect to Cyperf Controller {controller_ip}: {e}"
            ) from e

    async def fetch_attack_profiles(self) -> list[Any]:
        """Fetch all attack profiles from Cyperf Controller.

        Returns:
            List of attack profile objects from Cyperf API

        Raises:
            CyperfConnectionError: If connection to controller fails
            CyperfAPIError: If Cyperf API returns an error
        """
        if not self.client:
            raise CyperfConnectionError("Cyperf API client not initialized")

        try:
            start_time = time.time()
            logger.info("Fetching attack profiles from Cyperf Controller...")

            # Call the Cyperf API wrapper to get all attack profiles
            # Note: Assuming the wrapper has a method to fetch profiles
            # This will need to be validated against actual cyperf-api-wrapper API
            profiles = self.client.get_all_attack_profiles()

            duration = time.time() - start_time
            logger.info(f"✓ Fetched {len(profiles)} attack profiles from Cyperf in {duration:.2f}s")
            return profiles

        except AttributeError as e:
            # Method doesn't exist on client
            logger.error(f"Cyperf API method not found: {e}")
            raise CyperfAPIError(f"Cyperf API interface error: {e}") from e
        except ConnectionError as e:
            logger.error(f"Connection error while fetching profiles: {e}")
            raise CyperfConnectionError(f"Connection to Cyperf failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching profiles: {type(e).__name__}: {e}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise CyperfAPIError(f"Authentication failed: {e}") from e
            raise CyperfConnectionError(f"Failed to fetch profiles: {e}") from e

    def extract_cves_from_profiles(self, profiles: list[Any]) -> dict[str, str]:
        """Extract CVE IDs from attack profile metadata.

        Parses each profile's metadata to find CVE associations and maps them
        to profile names for later database storage.

        Args:
            profiles: List of attack profile objects from Cyperf API

        Returns:
            Dictionary mapping CVE ID to attack profile name: {cve_id: profile_name}
        """
        cve_mappings: dict[str, str] = {}

        logger.info(f"Extracting CVEs from {len(profiles)} attack profiles...")

        for i, profile in enumerate(profiles):
            try:
                # Profile structure assumed from Cyperf API
                # Expected: profile has 'name' field and either 'cves' list or metadata containing CVEs
                profile_name = profile.get("name", f"unknown_profile_{i}")

                # Try to get CVE list from profile
                cves = []
                if "cves" in profile:
                    # Direct CVE list
                    cves = (
                        profile["cves"] if isinstance(profile["cves"], list) else [profile["cves"]]
                    )
                elif "metadata" in profile and "cves" in profile.get("metadata", {}):
                    # CVEs in metadata
                    cves = profile["metadata"]["cves"]
                    if isinstance(cves, str):
                        cves = [cves]

                # Extract CVE IDs and map to profile
                for cve in cves:
                    if isinstance(cve, str):
                        cve_id = cve
                    elif isinstance(cve, dict):
                        cve_id = cve.get("id") or cve.get("cve_id")
                    else:
                        cve_id = str(cve)

                    if cve_id and isinstance(cve_id, str):
                        cve_mappings[cve_id] = profile_name

            except Exception as e:
                # Log warning but continue processing other profiles
                logger.warning(
                    f"Failed to parse CVEs from profile at index {i}: {e}; skipping this profile"
                )

        logger.info(f"✓ Extracted {len(cve_mappings)} CVE-to-profile mappings")
        return cve_mappings

    async def sync_cyperf_cves(self, retry_count: int = 0) -> SyncResult:
        """Orchestrate full CVE sync: fetch profiles, extract CVEs, return result.

        This is the main entry point for sync operations. It handles the complete
        cycle: fetch, parse, and prepare for database upsert.

        Args:
            retry_count: Internal use only; tracks retry attempts

        Returns:
            SyncResult with profiles_fetched, cves_extracted, and optional error message

        Note:
            Error handling is intentionally non-raising; errors are captured in
            the returned SyncResult for graceful degradation.
        """
        try:
            start_time = time.time()
            logger.info("Starting Cyperf sync operation...")

            # Fetch profiles from Cyperf
            profiles = await self.fetch_attack_profiles()
            profiles_count = len(profiles)

            # Extract CVEs from profiles
            cve_mappings = self.extract_cves_from_profiles(profiles)
            cves_count = len(cve_mappings)

            duration = time.time() - start_time
            logger.info(
                f"✓ Cyperf sync completed: fetched {profiles_count} profiles, "
                f"extracted {cves_count} CVEs in {duration:.2f}s"
            )

            return SyncResult(
                profiles_fetched=profiles_count,
                cves_extracted=cves_count,
                error=None,
            )

        except CyperfConnectionError as e:
            duration = time.time() - start_time
            logger.error(f"Connection error during sync (attempt {retry_count + 1}): {e}")
            return SyncResult(
                profiles_fetched=0,
                cves_extracted=0,
                error=f"Connection error: {str(e)}",
            )

        except CyperfAPIError as e:
            duration = time.time() - start_time
            logger.error(f"API error during sync: {e}")
            return SyncResult(
                profiles_fetched=0,
                cves_extracted=0,
                error=f"API error: {str(e)}",
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Unexpected error during sync: {type(e).__name__}: {e}")
            return SyncResult(
                profiles_fetched=0,
                cves_extracted=0,
                error=f"Unexpected error: {str(e)}",
            )
