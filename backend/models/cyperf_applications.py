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
