"""CVE API response schemas.

These are the API-facing Pydantic models used by routes/cve.py.
Separate from the ORM models in db/cve.py and the legacy models.py.

Key design decisions:
- cvss_v3_score and cvss_v4_score are float (not Decimal). Pydantic v2 serializes
  Decimal as a string in JSON, which breaks numeric comparisons in consumers.
- published_date is Optional[str] (ISO 8601 string) not Optional[datetime], to avoid
  serializer ambiguity when building from Redis-cached dicts vs DB ORM objects.
- testable: Optional[bool] is included so Phase 3 can populate it without schema change.
"""

from pydantic import BaseModel, Field


class CVEDetail(BaseModel):
    """Single CVE record — flattened, curated field set.

    Covers SEARCH-02 (full details) and BROWSE-04 (row display fields).
    """

    model_config = {"from_attributes": True}

    # Identity
    id: str = Field(..., description="CVE identifier (e.g. CVE-2024-1234)")
    description: str = Field(
        default="No description available",
        description="English description from NVD",
    )
    published_date: str | None = Field(None, description="Date CVE was published (ISO 8601 UTC)")

    # CVSS v3.1 — use float, not Decimal. Pydantic v2 serializes Decimal as string.
    cvss_v3_score: float | None = Field(
        None, description="CVSS v3.1 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v3_severity: str | None = Field(
        None, description="CVSS v3.1 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v3_vector: str | None = Field(None, description="CVSS v3.1 vector string")

    # CVSS v4.0 — present only for CVEs published post-2023 with v4 scoring
    cvss_v4_score: float | None = Field(
        None, description="CVSS v4.0 base score (0.0-10.0)", ge=0.0, le=10.0
    )
    cvss_v4_severity: str | None = Field(
        None, description="CVSS v4.0 severity: LOW | MEDIUM | HIGH | CRITICAL"
    )
    cvss_v4_vector: str | None = Field(None, description="CVSS v4.0 vector string")

    # References — deserialized list; DB stores JSON string, service layer deserializes
    reference_urls: list[str] = Field(
        default_factory=list,
        description="Reference URLs from NVD",
    )

    # Testability — populated from cverf_cve_strike_mappings via LEFT JOIN
    testable: bool = Field(False, description="True if at least one Cyperf Strike covers this CVE")
    attack_profiles: list[str] = Field(
        default_factory=list,
        description="All Cyperf Strike names that cover this CVE (empty list if not testable)",
    )


class CVESearchResponse(BaseModel):
    """Response envelope for /cve/search.

    Covers SEARCH-01 (search by CVE ID) and SEARCH-05 (severity filter).
    """

    results: list[CVEDetail]
    total: int = Field(..., description="Number of matching results returned")
    query: str = Field(..., description="Normalized query that was executed")
    search_type: str = Field(..., description="Search tier used: exact | prefix | fuzzy")


class CVELatestResponse(BaseModel):
    """Response envelope for /cve/latest.

    Covers BROWSE-01 (paginated table) and BROWSE-02 (sorted by published date).
    """

    results: list[CVEDetail]
    total: int = Field(..., description="Number of results in this page")
    page: int = Field(1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=500, description="Number of results per page")
    severity_filter: str | None = Field(None, description="Applied severity filter if any")


class ErrorResponse(BaseModel):
    """Structured error payload used in all 4xx/5xx handler detail fields.

    Ensures machine-readable error codes for client error handling.
    Never includes credential context.
    """

    error: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation")
    detail: str | None = Field(None, description="Additional context (never credentials)")
