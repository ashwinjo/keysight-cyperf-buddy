"""Pydantic models for request/response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# Import CVE API models
from .cve import CVEDetail, CVELatestResponse, CVESearchResponse, ErrorResponse


class CVEResponse(BaseModel):
    """CVE data response model."""

    id: str = Field(..., description="CVE identifier (e.g. CVE-2024-1234)")
    description: str | None = Field(None, description="CVE description from NVD")
    published_date: datetime | None = Field(None, description="Date CVE was published")
    last_modified: datetime | None = Field(None, description="Last modification date from NVD")

    cvss_v3_vector: str | None = Field(None, description="CVSS v3.1 vector string")
    cvss_v3_score: Decimal | None = Field(None, description="CVSS v3.1 score (0.0-10.0)")
    cvss_v3_severity: str | None = Field(
        None, description="CVSS v3.1 severity (LOW, MEDIUM, HIGH, CRITICAL)"
    )

    cvss_v4_vector: str | None = Field(None, description="CVSS v4.0 vector string")
    cvss_v4_score: Decimal | None = Field(None, description="CVSS v4.0 score (0.0-10.0)")
    cvss_v4_severity: str | None = Field(None, description="CVSS v4.0 severity")

    references: str | None = Field(None, description="JSON array of reference URLs")

    testable: bool = Field(False, description="Whether CVE can be tested with Cyperf")
    attack_profile: str | None = Field(
        None, description="Cyperf Attack Profile name that covers this CVE"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class CyperfMappingResponse(BaseModel):
    """Cyperf CVE mapping response model."""

    cve_id: str = Field(..., description="CVE ID that Cyperf can test")
    attack_profile_name: str = Field(..., description="Name of attack profile in Cyperf")
    attack_profile_id: str | None = Field(None, description="ID of attack profile")
    profile_version: str | None = Field(None, description="Version of attack profile")
    first_synced: datetime = Field(..., description="When this mapping was first synced")
    last_synced: datetime | None = Field(None, description="When mapping was last updated")
    is_deprecated: bool = Field(False, description="Whether profile is deprecated")

    class Config:
        """Pydantic config."""

        from_attributes = True


class SyncStatusResponse(BaseModel):
    """Sync metadata and status response."""

    last_successful_sync: str | None = Field(
        None, description="ISO 8601 datetime of last successful sync"
    )
    last_attempted_sync: str | None = Field(
        None, description="ISO 8601 datetime of last sync attempt"
    )
    sync_status: str | None = Field(
        None, description="Status of last run (success, failed, running, never)"
    )
    cverf_profiles_synced: int | None = Field(None, description="Number of profiles synced")
    cverf_cves_extracted: int | None = Field(None, description="Number of CVEs extracted")
    error_message: str | None = Field(None, description="Error message if last run failed")
    next_scheduled_sync: str | None = Field(
        None, description="ISO 8601 datetime of next scheduled sync"
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall status (ok, degraded, error)")
    service: str | None = Field(None, description="Service being checked")
    error: str | None = Field(None, description="Error message if status is not ok")


__all__ = [
    "CVEResponse",
    "CyperfMappingResponse",
    "SyncStatusResponse",
    "HealthResponse",
    "CVEDetail",
    "CVESearchResponse",
    "CVELatestResponse",
    "ErrorResponse",
]
