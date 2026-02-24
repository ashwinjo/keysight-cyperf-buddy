"""NVD API async wrapper.

nvdlib is synchronous (requests-based). All calls are wrapped in asyncio.to_thread()
to prevent event loop blocking in FastAPI async routes.

Rate-limit detection: nvdlib does not use typed exceptions for HTTP errors. We inspect
the exception string for '429', '403', or 'rate' to classify as NVDRateLimitError.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import nvdlib
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

logger = logging.getLogger(__name__)


class NVDRateLimitError(Exception):
    """Raised when NVD returns 429 or equivalent rate-limit signal."""

    pass


class NVDClient:
    """Thread-safe async wrapper around nvdlib.

    Wraps all synchronous nvdlib calls in asyncio.to_thread() to prevent
    event loop blocking. The API key controls the minimum delay between
    requests (0.6s with key, 6.0s without).
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        # nvdlib enforces delays internally between paginated requests
        # When using an API key, we can specify a custom delay; without a key, nvdlib uses 6s default
        # DO NOT pass delay parameter when key is None - nvdlib will raise SyntaxError
        self._delay: float | None = 0.6 if api_key else None
        if api_key:
            logger.info("NVDClient initialized with API key (100 req/min limit, 0.6s delay)")
        else:
            logger.info(
                "NVDClient initialized without API key (10 req/min limit, 6.0s default delay). "
                "Set NVD_API_KEY environment variable for production use."
            )

    async def fetch_cve(self, cve_id: str) -> object | None:
        """Fetch a single CVE by exact ID.

        Returns the nvdlib CVE object if found, None if not in NVD.
        Raises NVDRateLimitError if NVD is rate-limiting.
        """
        normalized_id = cve_id.upper().strip()
        logger.debug("Fetching CVE from NVD: %s", normalized_id)

        def _sync_fetch() -> list:
            # Only pass delay if we have an API key (nvdlib raises SyntaxError if delay without key)
            kwargs = {"cveId": normalized_id, "key": self._api_key}
            if self._delay is not None:
                kwargs["delay"] = self._delay
            return nvdlib.searchCVE(**kwargs)

        try:
            results = await asyncio.to_thread(_sync_fetch)
            return results[0] if results else None
        except Exception as exc:
            self._classify_and_raise(exc, context=normalized_id)

    async def fetch_latest(
        self,
        days: int = 30,
        limit: int = 500,
    ) -> list[object]:
        """Fetch CVEs published in the last N days.

        Uses searchCVE_V2 (generator) to avoid loading the full result set
        into memory when date windows span many CVEs. Collects up to `limit`
        results before returning.

        Severity filtering is NOT applied here — post-filter in cve_service.py
        because v4.0 severity is not a supported NVD API parameter in nvdlib.
        """
        start, end = _get_date_window(days)
        logger.debug(
            "Fetching latest CVEs from NVD: window=%s to %s, limit=%d",
            start,
            end,
            limit,
        )

        def _sync_fetch() -> list:
            # searchCVE_V2 returns a generator; collect up to limit records
            # Only pass delay if we have an API key (nvdlib raises SyntaxError if delay without key)
            kwargs = {"pubStartDate": start, "pubEndDate": end, "key": self._api_key}
            if self._delay is not None:
                kwargs["delay"] = self._delay

            results = []
            for cve in nvdlib.searchCVE_V2(**kwargs):
                results.append(cve)
                if len(results) >= limit:
                    break
            return results

        try:
            return await asyncio.to_thread(_sync_fetch)
        except Exception as exc:
            self._classify_and_raise(exc, context=f"latest (days={days})")

    def _classify_and_raise(self, exc: Exception, context: str) -> None:
        """Inspect exception and raise NVDRateLimitError or re-raise original.

        nvdlib does not use typed exceptions for HTTP errors; inspect the
        string representation to detect 429/403 rate-limit scenarios.
        """
        exc_str = str(exc).lower()
        if any(signal in exc_str for signal in ("429", "403", "rate limit", "too many")):
            logger.warning("NVD rate limit hit for: %s", context)
            raise NVDRateLimitError(f"NVD API rate limited while fetching: {context}") from exc
        # Unknown error — re-raise with context but do not swallow
        logger.error("NVD API error for %s: %s", context, exc, exc_info=True)
        raise exc


def _get_date_window(days: int) -> tuple[str, str]:
    """Return (start, end) date strings in NVD API format: 'YYYY-MM-DD HH:MM'.

    NVD enforces a maximum 120-day window per query.
    """
    if days > 120:
        raise ValueError(f"NVD API allows max 120-day date window; requested {days} days")
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    return (
        start.strftime("%Y-%m-%d %H:%M"),
        now.strftime("%Y-%m-%d %H:%M"),
    )


def extract_cve_fields(nvd_cve: object) -> dict:
    """Map nvdlib CVE object attributes to the application's field schema.

    This is the single translation boundary between nvdlib's attribute
    namespace and the application's field names. All attribute access uses
    getattr(obj, attr, None) because not all CVEs have all CVSS versions.

    CVSS v3 preference: v3.1 over v3.0 (older CVEs only have v3.0).
    CVSS v4: present only on CVEs published after 2023.
    References: extract .url from each ref object, skip None URLs.
    """
    # English description
    description = "No description available"
    if hasattr(nvd_cve, "descriptions") and nvd_cve.descriptions:
        for desc in nvd_cve.descriptions:
            if getattr(desc, "lang", "") == "en":
                description = desc.value
                break

    # Published date: ISO 8601 string from nvdlib; normalize to bare isoformat
    published_date: str | None = None
    raw_published = getattr(nvd_cve, "published", None)
    if raw_published:
        try:
            # nvdlib returns strings like "2024-01-15T10:00:00.000"
            published_date = datetime.fromisoformat(raw_published.rstrip("Z")).isoformat()
        except (ValueError, AttributeError):
            published_date = None

    # Reference URLs
    reference_urls: list[str] = []
    refs = getattr(nvd_cve, "references", None)
    if refs:
        reference_urls = [ref.url for ref in refs if hasattr(ref, "url") and ref.url]

    # CVSS v3.1 preferred; fall back to v3.0 for older CVEs
    cvss_v3_score = getattr(nvd_cve, "v31score", None) or getattr(nvd_cve, "v30score", None)
    cvss_v3_severity = getattr(nvd_cve, "v31severity", None) or getattr(
        nvd_cve, "v30severity", None
    )
    cvss_v3_vector = getattr(nvd_cve, "v31vector", None) or getattr(nvd_cve, "v30vector", None)

    # CVSS v4.0 — nvdlib >= 0.7.6 required
    cvss_v4_score = getattr(nvd_cve, "v40score", None)
    cvss_v4_severity = getattr(nvd_cve, "v40severity", None)
    cvss_v4_vector = getattr(nvd_cve, "v40vector", None)

    # CNA (CVE Numbering Authority) — from sourceIdentifier (email/ID of reporting organization)
    cna: str | None = getattr(nvd_cve, "sourceIdentifier", None)

    return {
        "id": nvd_cve.id,
        "description": description,
        "published_date": published_date,
        "cvss_v3_score": float(cvss_v3_score) if cvss_v3_score is not None else None,
        "cvss_v3_severity": cvss_v3_severity.upper() if cvss_v3_severity else None,
        "cvss_v3_vector": cvss_v3_vector,
        "cvss_v4_score": float(cvss_v4_score) if cvss_v4_score is not None else None,
        "cvss_v4_severity": cvss_v4_severity.upper() if cvss_v4_severity else None,
        "cvss_v4_vector": cvss_v4_vector,
        "reference_urls": reference_urls,
        "cna": cna,
        # Testability defaults — populated by cve_service after querying cverf_cve_strike_mappings
        "testable": False,
        "attack_profiles": [],
    }


# ---------------------------------------------------------------------------
# Retry-wrapped fetch functions (standalone to allow @retry decoration cleanly)
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type(NVDRateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_cve_with_retry(
    nvd_client: NVDClient,
    cve_id: str,
) -> object | None:
    """Fetch CVE from NVD with exponential backoff on rate-limit.

    Attempts: 3 total.
    Wait sequence: ~2s, ~4s, ~8s (+ 0-2s jitter each).
    On exhaustion: raises NVDRateLimitError (caught in cve_service.py fallback).
    """
    return await nvd_client.fetch_cve(cve_id)


@retry(
    retry=retry_if_exception_type(NVDRateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30) + wait_random(0, 2),
    stop=stop_after_attempt(3),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def fetch_latest_with_retry(
    nvd_client: NVDClient,
    days: int = 30,
    limit: int = 500,
) -> list[object]:
    """Fetch latest CVEs with exponential backoff on rate-limit.

    Same retry policy as fetch_cve_with_retry.
    On exhaustion: raises NVDRateLimitError (caught in cve_service.py).
    """
    return await nvd_client.fetch_latest(days=days, limit=limit)
