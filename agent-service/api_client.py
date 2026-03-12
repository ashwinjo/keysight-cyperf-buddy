"""Async httpx client for the main CyperfBuddy backend API with retry logic."""

import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class BackendAPIClient:
    def __init__(self, base_url: str, timeout: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def get_cyperf_apps(self) -> list[dict]:
        """Fetch all Cyperf application profiles from the backend.

        Returns the 'results' list from GET /cyperf-applications.
        Raises httpx.HTTPError on failure after 3 retry attempts.
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/cyperf-applications"
            logger.debug("GET %s", url)
            response = await client.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def get_cyperf_strikes(self) -> list[dict]:
        """Fetch all Cyperf strike profiles from the backend.

        Returns the 'results' list from GET /cyperf-applications/strikes.
        Raises httpx.HTTPError on failure after 3 retry attempts.
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/cyperf-applications/strikes"
            logger.debug("GET %s", url)
            response = await client.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
