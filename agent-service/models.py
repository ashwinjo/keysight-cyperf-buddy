"""Pydantic request/response schemas for the L4-7 Test Advisor agent service."""

from typing import Literal

from pydantic import BaseModel, Field


class L47ScenarioRequest(BaseModel):
    testing_focus: Literal["app_performance", "security_attacks", "both"]
    use_case: str = Field(..., min_length=10, max_length=1000)
    objectives: str = Field(..., min_length=10, max_length=1000)
    timeline: str = Field(..., min_length=5, max_length=200)


class Recommendation(BaseModel):
    rank: int
    profile_name: str
    profile_type: Literal["application", "strike"]
    rationale: str


class L47RecommendationResponse(BaseModel):
    success: bool
    message: str
    recommendations: list[Recommendation]
