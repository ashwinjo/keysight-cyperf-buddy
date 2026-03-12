"""Pydantic models for Cyperf applications API responses."""

from pydantic import BaseModel


class CyperfApplicationResponse(BaseModel):
    """Single Cyperf application record."""

    id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class CyperfApplicationListResponse(BaseModel):
    """List of Cyperf applications."""

    results: list[CyperfApplicationResponse]
    total: int


class CyperfApplicationTypeResponse(BaseModel):
    """Single Cyperf application type record."""

    id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class CyperfApplicationTypeListResponse(BaseModel):
    """List of Cyperf application types."""

    results: list[CyperfApplicationTypeResponse]
    total: int


class CyperfStrikeResponse(BaseModel):
    """Single Cyperf strike name from cverf_cve_strike_mappings."""

    strike_name: str


class CyperfStrikeListResponse(BaseModel):
    """Paginated list of Cyperf strike names."""

    results: list[CyperfStrikeResponse]
    total: int
