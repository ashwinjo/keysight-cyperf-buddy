"""Hybrid keyword + fuzzy ranking for Cyperf profile selection."""

import logging
from typing import NamedTuple

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class RankedProfile(NamedTuple):
    profile_name: str
    profile_type: str
    score: float
    rationale: str


def rank_profiles_hybrid(
    profiles: list[dict],
    user_scenario: str,
    top_k: int = 3,
) -> list[RankedProfile]:
    """Rank profiles using a hybrid keyword + fuzzy score.

    Each profile dict must contain:
      - 'name': str  (normalised profile name)
      - 'description': str  (may be empty)
      - 'type': str  ('application' or 'strike')

    Scoring:
      keyword_score = |scenario_words ∩ profile_words| / max(|scenario_words|, 1)
      fuzzy_score   = token_sort_ratio(profile_text, scenario) / 100
      composite     = 0.6 * keyword_score + 0.4 * fuzzy_score

    Rationale thresholds:
      score > 0.7  → "Strong match"
      score > 0.4  → "Relevant match"
      else         → "Potential match"
    """
    if not profiles:
        return []

    scenario_lower = user_scenario.lower()
    scenario_words = {w for w in scenario_lower.split() if len(w) > 3}

    scored: list[RankedProfile] = []
    for profile in profiles:
        name = profile.get("name", "")
        description = profile.get("description", "")
        profile_type = profile.get("type", "application")
        profile_text = f"{name} {description}".lower()

        profile_words = set(profile_text.split())
        keyword_score = len(scenario_words & profile_words) / max(
            len(scenario_words), 1
        )
        fuzzy_score = fuzz.token_sort_ratio(profile_text, scenario_lower) / 100.0
        composite = 0.6 * keyword_score + 0.4 * fuzzy_score

        if composite > 0.7:
            rationale = f"Strong match: {name} directly addresses your scenario."
        elif composite > 0.4:
            rationale = (
                f"Relevant match: {name} covers key aspects of your testing objectives."
            )
        else:
            rationale = f"Potential match: {name} may address parts of your scenario."

        scored.append(
            RankedProfile(
                profile_name=name,
                profile_type=profile_type,
                score=composite,
                rationale=rationale,
            )
        )

    top = sorted(scored, key=lambda x: x.score, reverse=True)[:top_k]
    logger.debug(
        "Ranked %d profiles; top %d: %s",
        len(profiles),
        len(top),
        [p.profile_name for p in top],
    )
    return top
