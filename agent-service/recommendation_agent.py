"""Orchestration layer: fetches Cyperf profiles, ranks them, and uses Gemini for rationale."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import google.generativeai as genai

from api_client import BackendAPIClient
from config import AgentSettings
from models import L47ScenarioRequest, Recommendation
from ranking import RankedProfile, rank_profiles_hybrid

logger = logging.getLogger(__name__)

_CACHE_TTL = timedelta(hours=1)


@dataclass
class _ProfileCache:
    profiles: list[dict] = field(default_factory=list)
    refreshed_at: datetime | None = None

    def is_valid(self) -> bool:
        return (
            self.refreshed_at is not None
            and datetime.utcnow() - self.refreshed_at < _CACHE_TTL
        )


class RecommendationAgent:
    """Stateful agent that holds per-bucket profile caches for the process lifetime."""

    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self.api_client = BackendAPIClient(
            base_url=settings.backend_api_url,
            timeout=settings.backend_timeout_seconds,
        )
        # Separate cache per profile type — avoids fetching 6000 records
        # when only apps or strikes are needed.
        self._cache: dict[str, _ProfileCache] = {
            "apps": _ProfileCache(),
            "strikes": _ProfileCache(),
        }
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    async def recommend(self, req: L47ScenarioRequest) -> list[Recommendation]:
        """Return top-3 ranked recommendations for the given L4-7 scenario.

        Steps:
        1. Fetch candidate profiles based on testing_focus (cache-first, TTL=1h)
        2. Rank with hybrid algorithm locally (fast Python string ops)
        3. Call Gemini to generate rationale for top-k only (never full profile list)
        4. Return structured Recommendation list
        """
        candidates = await self._fetch_candidates(req.testing_focus)
        if not candidates:
            return []

        metric_context = " ".join(
            filter(None, [req.application_metric, req.attacks_metric])
        )
        user_scenario = f"{req.use_case} {metric_context}".strip()
        ranked = rank_profiles_hybrid(candidates, user_scenario, top_k=3)

        return await self._generate_recommendations(ranked, req)

    async def _fetch_candidates(self, testing_focus: str) -> list[dict]:
        """Return profiles for the given testing_focus from cache or backend.

        Cache buckets are independent: app_performance only warms 'apps',
        security_attacks only warms 'strikes', both warms both concurrently.
        Returns empty list on backend failure (graceful degradation).
        """
        try:
            if testing_focus == "Application Profile":
                return await self._get_apps()
            elif testing_focus == "Security / Attacks":
                return await self._get_strikes()
            else:  # Both — fetch in parallel on cold start
                apps, strikes = await asyncio.gather(
                    self._get_apps(),
                    self._get_strikes(),
                )
                return apps + strikes
        except Exception as exc:
            logger.warning("Backend API fetch failed: %s", exc)
            return []

    async def _get_apps(self) -> list[dict]:
        if not self._cache["apps"].is_valid():
            logger.info("Cache miss: fetching application profiles from backend")
            items = await self.api_client.get_cyperf_apps()
            self._cache["apps"].profiles = [
                {
                    "name": i["name"],
                    "description": i.get("description", ""),
                    "type": "application",
                }
                for i in items
            ]
            self._cache["apps"].refreshed_at = datetime.utcnow()
            logger.info(
                "Cache populated: %d application profiles",
                len(self._cache["apps"].profiles),
            )
        return self._cache["apps"].profiles

    async def _get_strikes(self) -> list[dict]:
        if not self._cache["strikes"].is_valid():
            logger.info("Cache miss: fetching strike profiles from backend")
            items = await self.api_client.get_cyperf_strikes()
            self._cache["strikes"].profiles = [
                {
                    "name": i["strike_name"],
                    "description": i["strike_name"],
                    "type": "strike",
                }
                for i in items
            ]
            self._cache["strikes"].refreshed_at = datetime.utcnow()
            logger.info(
                "Cache populated: %d strike profiles",
                len(self._cache["strikes"].profiles),
            )
        return self._cache["strikes"].profiles

    async def _generate_recommendations(
        self,
        ranked: list[RankedProfile],
        req: L47ScenarioRequest,
    ) -> list[Recommendation]:
        """Use Gemini to generate 2-3 sentence rationale for each ranked profile.

        Falls back to ranking.py template rationale if Gemini call fails.
        """
        recommendations: list[Recommendation] = []
        for i, profile in enumerate(ranked, start=1):
            try:
                rationale = await self._gemini_rationale(profile, req)
            except Exception as exc:
                logger.warning(
                    "Gemini rationale failed for %s: %s — using template",
                    profile.profile_name,
                    exc,
                )
                rationale = profile.rationale  # Fallback to ranking template

            recommendations.append(
                Recommendation(
                    rank=i,
                    profile_name=profile.profile_name,
                    profile_type=profile.profile_type,
                    rationale=rationale,
                )
            )
        return recommendations

    async def _gemini_rationale(
        self, profile: RankedProfile, req: L47ScenarioRequest
    ) -> str:
        """Ask Gemini to write a 2-3 sentence rationale for why this profile fits.

        Runs synchronously via asyncio.to_thread() since google-generativeai SDK is sync.
        """
        profile_label = (
            "application profile" if profile.profile_type == "application" else "strike"
        )
        metric_line = ""
        if req.application_metric:
            metric_line += f"Application metric: {req.application_metric}\n"
        if req.attacks_metric:
            metric_line += f"Attacks metric: {req.attacks_metric}\n"
        automation_line = "Automation needed: yes\n" if req.needs_automation else ""
        prompt = (
            f"You are a network testing expert. In 2-3 concise sentences, explain why "
            f"the Cyperf {profile_label} named '{profile.profile_name}' is a good fit "
            f"for this L4-7 test scenario:\n\n"
            f"Use case: {req.use_case}\n"
            f"{metric_line}"
            f"{automation_line}"
            f"\nBe specific to the profile name and scenario. No generic advice."
        )
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 150},
        )
        return response.text.strip()
