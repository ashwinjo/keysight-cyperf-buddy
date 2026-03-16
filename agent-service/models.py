"""Pydantic request/response schemas for the L4-7 Test Advisor agent service."""

from typing import Literal

from pydantic import BaseModel, Field


class L47ScenarioRequest(BaseModel):
    testing_focus: Literal["Application Profile", "Security / Attacks", "Both"]
    application_metric: str | None = Field(default=None, max_length=500)
    attacks_metric: str | None = Field(default=None, max_length=500)
    use_case: str = Field(..., min_length=10, max_length=1000)
    needs_automation: bool = Field(default=False)


class Recommendation(BaseModel):
    rank: int
    profile_name: str
    profile_type: Literal["application", "strike"]
    rationale: str


class L47RecommendationResponse(BaseModel):
    success: bool
    message: str
    recommendations: list[Recommendation]
