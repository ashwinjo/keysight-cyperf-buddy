"""Pydantic models for request/response schemas."""

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

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
    attack_profiles: list[str] = Field(
        default_factory=list,
        description="All Cyperf Strike names that cover this CVE (empty list if not testable)",
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


class EndpointConfigRequest(BaseModel):
    """Request to update the Keysight CyPerf Controller endpoint."""

    endpoint: str = Field(
        ...,
        description="Keysight CyPerf Controller endpoint (DNS name or IP address)",
        examples=["cyperf.example.com", "192.168.1.100"],
    )

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint_format(cls, v: str) -> str:
        """Validate endpoint is non-empty and a valid DNS name or IP address.

        Strips http:// or https:// prefix if present.
        Rejects endpoints that embed credentials (@ character).
        Accepts IPv4, IPv6 (bracket notation), domain names, and bare IPs.

        Args:
            v: Raw endpoint string from the request body.

        Returns:
            Cleaned endpoint string with protocol prefix removed.

        Raises:
            ValueError: If endpoint is empty, contains credentials, or has invalid chars.
        """
        if not v or not v.strip():
            raise ValueError("Endpoint cannot be empty")

        # Remove protocol prefix if present (caller may include it)
        v = v.replace("https://", "").replace("http://", "").strip()

        if not v:
            raise ValueError("Endpoint cannot be empty after stripping protocol prefix")

        # Reject credentials embedded in URL (user:pass@host pattern)
        if "@" in v:
            raise ValueError(
                "Endpoint must not contain credentials; provide hostname or IP address only"
            )

        # Allow IPv4, IPv6 bracket notation [::1], domain names, optional port suffix
        # Pattern: alphanumeric, dots, hyphens, underscores, brackets (IPv6), colons (port/IPv6)
        if not re.match(r"^[a-zA-Z0-9._\-\[\]:]+$", v):
            raise ValueError(
                "Invalid endpoint format — only alphanumeric characters, dots, "
                "hyphens, underscores, brackets, and colons are allowed"
            )

        return v


class EndpointConfigResponse(BaseModel):
    """Response containing the current CyPerf endpoint configuration."""

    endpoint: str = Field(..., description="Current CyPerf Controller endpoint")
    last_validated_at: datetime | None = Field(
        None, description="ISO 8601 timestamp of last successful connectivity validation"
    )
    is_valid: bool = Field(
        False, description="Whether the endpoint was reachable at last validation"
    )
    error_message: str | None = Field(
        None, description="Human-readable error from last failed validation attempt"
    )

    class Config:
        """Pydantic config: allow ORM-mode attribute access."""

        from_attributes = True


__all__ = [
    "CVEResponse",
    "CyperfMappingResponse",
    "SyncStatusResponse",
    "HealthResponse",
    "CVEDetail",
    "CVESearchResponse",
    "CVELatestResponse",
    "ErrorResponse",
    "EndpointConfigRequest",
    "EndpointConfigResponse",
]
