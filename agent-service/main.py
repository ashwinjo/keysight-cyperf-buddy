"""CyperfBuddy L4-7 Test Advisor — FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import get_settings
from models import L47RecommendationResponse, L47ScenarioRequest
from recommendation_agent import RecommendationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate settings and instantiate the agent at startup."""
    settings = get_settings()  # Fails fast if GEMINI_API_KEY is missing
    app.state.agent = RecommendationAgent(settings)
    logger.info("L4-7 Test Advisor ready — backend: %s", settings.backend_api_url)
    yield
    logger.info("L4-7 Test Advisor shutting down")


app = FastAPI(
    title="CyperfBuddy L4-7 Test Advisor",
    description="Recommends Cyperf Application and Strike profiles for L4-7 test scenarios.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten Pydantic validation error arrays into a plain string.

    Prevents the frontend from receiving unrenderable objects.
    """
    errors = exc.errors()
    messages = []
    for error in errors:
        loc = " -> ".join(str(part) for part in error.get("loc", []) if part != "body")
        msg = error.get("msg", "Invalid value")
        messages.append(f"{loc}: {msg}" if loc else msg)
    detail = "; ".join(messages)
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "service": "l47-advisor"}


@app.post("/api/l47/recommend", response_model=L47RecommendationResponse)
async def recommend(
    request: Request, body: L47ScenarioRequest
) -> L47RecommendationResponse:
    """Return top-3 ranked Cyperf profile recommendations for the given L4-7 scenario.

    Always returns HTTP 200. Returns empty recommendations with a plain-language
    message when no matching profiles are found or if the backend is unreachable.
    """
    if (
        body.testing_focus in ("Application Profile", "Both")
        and not body.application_metric
    ):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "application_metric is required when testing_focus includes Application Profile"
            },
        )
    if body.testing_focus in ("Security / Attacks", "Both") and not body.attacks_metric:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "attacks_metric is required when testing_focus includes Security / Attacks"
            },
        )

    agent: RecommendationAgent = request.app.state.agent
    try:
        recommendations = await agent.recommend(body)
    except Exception as exc:
        logger.exception("Unexpected error in recommend endpoint: %s", exc)
        return L47RecommendationResponse(
            success=True,
            message="An unexpected error occurred. Please try again later.",
            recommendations=[],
        )

    if not recommendations:
        return L47RecommendationResponse(
            success=True,
            message=(
                "No matching profiles found. "
                "Try a more specific use case or ensure backend data is synced."
            ),
            recommendations=[],
        )

    return L47RecommendationResponse(
        success=True,
        message=f"Generated {len(recommendations)} recommendations",
        recommendations=recommendations,
    )
