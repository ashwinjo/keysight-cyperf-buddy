"""AshRAI Questionnaire router: POST /ashrai/recommend.

Validates questionnaire answers about Cyperf testing needs and generates
personalized recommendations for test configuration, metrics, and automation.

Input: questionnaire answers (testing focus, metrics, use case, automation needs)
Output: structured recommendations for Cyperf setup
"""

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ashrai", tags=["ashrai"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class QuestionnaireRequest(BaseModel):
    """Validated questionnaire answers from user."""

    testing_focus: Literal["Application Profile", "Security / Attacks", "Both"]
    application_metric: str | None = Field(
        default=None, min_length=1, max_length=100, description="e.g., connections per second"
    )
    attacks_metric: str | None = Field(
        default=None, min_length=1, max_length=100, description="e.g., attacks per second"
    )
    use_case: str = Field(..., min_length=5, max_length=500, description="Detailed use case")
    needs_automation: bool = Field(default=False)


class Recommendation(BaseModel):
    """Single recommendation item."""

    title: str
    description: str
    priority: Literal["high", "medium", "low"]
    category: Literal["configuration", "metrics", "automation", "topology", "validation"]


class RecommendationResponse(BaseModel):
    """Response with personalized Cyperf testing recommendations."""

    success: bool
    message: str
    testing_focus: str
    recommendations: list[Recommendation]
    next_steps: list[str]


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------


def _generate_recommendations(req: QuestionnaireRequest) -> list[Recommendation]:
    """Generate recommendations based on questionnaire answers.

    Args:
        req: Validated questionnaire request

    Returns:
        List of Recommendation objects
    """
    recommendations: list[Recommendation] = []

    # 1. Testing focus recommendations
    if req.testing_focus in ["Application Profile", "Both"]:
        recommendations.append(
            Recommendation(
                title="Configure Application Profile Testing",
                description=f"Set up application profile tests to measure {req.application_metric or 'performance metrics'}",
                priority="high",
                category="configuration",
            )
        )

        # Use case-specific app recommendations
        if "video" in req.use_case.lower() or "stream" in req.use_case.lower():
            recommendations.append(
                Recommendation(
                    title="Enable Stateful Video Traffic Profiles",
                    description="Use Cyperf's video streaming profiles (HLS, DASH) for realistic stateful testing",
                    priority="high",
                    category="configuration",
                )
            )
            recommendations.append(
                Recommendation(
                    title="Monitor Video QoE Metrics",
                    description="Track bitrate, rebuffering events, and latency impact on video playback quality",
                    priority="high",
                    category="metrics",
                )
            )

        if "stateful" in req.use_case.lower():
            recommendations.append(
                Recommendation(
                    title="Enable Session Persistence",
                    description="Configure cookie-based or header-based session tracking for stateful interactions",
                    priority="high",
                    category="configuration",
                )
            )

    # 2. Security/Attacks recommendations
    if req.testing_focus in ["Security / Attacks", "Both"]:
        recommendations.append(
            Recommendation(
                title="Configure Attack Strike Testing",
                description=f"Set up security strike tests to measure {req.attacks_metric or 'attack throughput'}",
                priority="high",
                category="configuration",
            )
        )
        recommendations.append(
            Recommendation(
                title="Define Attack Profiles",
                description="Select relevant attack types (DDoS, volumetric, application-layer) matching your threat model",
                priority="high",
                category="configuration",
            )
        )

    # 3. Automation recommendations
    if req.needs_automation:
        recommendations.append(
            Recommendation(
                title="Set Up Test Automation",
                description="Create automated test scenarios that run on schedule or trigger on events",
                priority="high",
                category="automation",
            )
        )
        recommendations.append(
            Recommendation(
                title="Implement Result Export & Alerting",
                description="Configure automated exports to monitoring systems and alerting on threshold breaches",
                priority="medium",
                category="automation",
            )
        )

    # 4. Topology recommendations
    if "live" in req.use_case.lower() or "production" in req.use_case.lower():
        recommendations.append(
            Recommendation(
                title="Use Multi-Zone Test Topology",
                description="Distribute test clients across multiple geographic zones for realistic traffic patterns",
                priority="medium",
                category="topology",
            )
        )

    # 5. Validation recommendations (common for all)
    recommendations.append(
        Recommendation(
            title="Establish Baseline Metrics",
            description="Run initial tests to establish healthy baseline metrics before optimization",
            priority="medium",
            category="validation",
        )
    )

    # Avoid duplicates
    seen = set()
    unique_recommendations = []
    for rec in recommendations:
        key = (rec.title, rec.description)
        if key not in seen:
            seen.add(key)
            unique_recommendations.append(rec)

    return unique_recommendations


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(req: QuestionnaireRequest) -> RecommendationResponse:
    """Generate personalized Cyperf testing recommendations.

    Takes questionnaire answers about testing needs and returns a prioritized
    list of recommendations for configuration, metrics, and automation setup.

    Args:
        req: QuestionnaireRequest with validated answers

    Returns:
        RecommendationResponse with recommendations and next steps

    Raises:
        HTTPException: If validation fails (422)
    """
    try:
        # Validate that at least one testing focus requires metrics
        if req.testing_focus == "Application Profile" and not req.application_metric:
            raise HTTPException(
                status_code=422,
                detail="application_metric is required when testing_focus is 'Application Profile'",
            )

        if req.testing_focus == "Security / Attacks" and not req.attacks_metric:
            raise HTTPException(
                status_code=422,
                detail="attacks_metric is required when testing_focus is 'Security / Attacks'",
            )

        # Generate recommendations
        recommendations = _generate_recommendations(req)

        # Define next steps based on focus
        next_steps = [
            "1. Review recommendations above and prioritize by your timeline",
            "2. Configure your test topology in Cyperf GUI or CLI",
            "3. Create test profiles matching your use case",
        ]

        if req.needs_automation:
            next_steps.append("4. Set up test automation and scheduling")
            next_steps.append("5. Configure result export and monitoring integration")

        next_steps.append("6. Run baseline test to establish healthy metrics")

        logger.info(
            "Generated recommendations testing_focus=%s use_case=%s recommendations_count=%d",
            req.testing_focus,
            req.use_case[:50],
            len(recommendations),
        )

        return RecommendationResponse(
            success=True,
            message=f"Generated {len(recommendations)} personalized recommendations for {req.testing_focus.lower()} testing",
            testing_focus=req.testing_focus,
            recommendations=recommendations,
            next_steps=next_steps,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Recommendation generation failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(status_code=500, detail="Failed to generate recommendations") from exc
