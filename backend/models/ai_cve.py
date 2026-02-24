"""Pydantic response models for the AI CVE API.

These models bridge the AICve ORM columns to the shape expected by
the frontend useAiCVEs() hook (frontend/src/types/api.ts AiCVEResponse).

Field mapping (ORM -> API):
  AICve.cve_id        -> AiCVEResponse.id        (synthetic NoCVE_cyperf<uuid5> ID)
  AICve.strike_name   -> AiCVEResponse.ai_strike_name
  AICve.created_at    -> AiCVEResponse.generated_at (ISO 8601 string)
  description         -> None  (not stored in ai_cves; enrichment is a future concern)
  severity            -> None  (not stored in ai_cves)
  cvss_score          -> None  (not stored in ai_cves)

Note: AICve.id (uuid4 surrogate PK) is intentionally NOT exposed; cve_id
is the stable external identifier that clients should use for bookmarking.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AiCVEResponse(BaseModel):
    """Single AI CVE record — matches frontend AiCVEResponse type contract.

    Fields description, severity, and cvss_score are nullable because ai_cves
    does not store CVSS metadata. They are returned as null until enrichment
    from a secondary source is implemented.
    """

    id: str
    description: str | None = None
    severity: str | None = None
    cvss_score: float | None = None
    ai_strike_name: str | None = None
    generated_at: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_row(cls, row: Any) -> AiCVEResponse:
        """Construct AiCVEResponse from an AICve ORM row.

        Handles the field rename (cve_id -> id, strike_name -> ai_strike_name)
        and serialises created_at to ISO 8601 string with trailing Z.
        """
        generated_at: str | None = None
        if row.created_at is not None:
            generated_at = row.created_at.isoformat() + "Z"

        return cls(
            id=row.cve_id,
            description=None,
            severity=None,
            cvss_score=None,
            ai_strike_name=row.strike_name,
            generated_at=generated_at,
        )


class AiCVEListResponse(BaseModel):
    """Paginated list of AI CVE records.

    Matches the shape the frontend useAiCVEs() hook expects:
      res.data.results  — list of AiCVEResponse
      res.data.total    — total row count (unpaged)
    """

    results: list[AiCVEResponse]
    total: int
