"""Unit tests for ranking logic and Pydantic models."""

import sys
import os

# Ensure agent-service root is on path for direct module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from ranking import rank_profiles_hybrid, RankedProfile
from models import L47ScenarioRequest, L47RecommendationResponse


def test_rank_profiles_returns_top_k(sample_apps):
    """rank_profiles_hybrid returns at most top_k results."""
    ranked = rank_profiles_hybrid(
        sample_apps, "HTTP load balancer performance", top_k=2
    )
    assert len(ranked) <= 2
    assert all(isinstance(r, RankedProfile) for r in ranked)


def test_rank_profiles_sorted_descending(sample_apps):
    """Results are sorted by score descending."""
    ranked = rank_profiles_hybrid(sample_apps, "HTTP traffic performance", top_k=3)
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_profiles_http_scores_highest(sample_apps):
    """HTTP-related profile appears in top results for HTTP-focused scenario."""
    ranked = rank_profiles_hybrid(sample_apps, "HTTP traffic performance test", top_k=3)
    # At minimum, HTTP Traffic should appear in top results for an HTTP-specific scenario
    assert ranked, "Expected at least one ranked result"
    profile_names = [r.profile_name for r in ranked]
    assert (
        "HTTP Traffic" in profile_names
    ), f"Expected HTTP Traffic in top results, got {profile_names}"


def test_rank_profiles_empty_input():
    """Empty candidates returns empty list."""
    ranked = rank_profiles_hybrid([], "any scenario", top_k=3)
    assert ranked == []


def test_l47_request_validation_missing_field():
    """L47ScenarioRequest raises ValidationError when required field missing."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        L47ScenarioRequest(
            testing_focus="app_performance",
            use_case="short",  # Too short (min_length=10)
            objectives="valid objectives text here",
            timeline="2 weeks",
        )


def test_l47_request_valid_fields(sample_request_app):
    """L47ScenarioRequest accepts valid input."""
    req = L47ScenarioRequest(**sample_request_app)
    assert req.testing_focus == "app_performance"


def test_recommendation_response_no_next_steps():
    """L47RecommendationResponse does not have next_steps field (per CONTEXT.md)."""
    resp = L47RecommendationResponse(success=True, message="ok", recommendations=[])
    assert not hasattr(
        resp, "next_steps"
    ), "next_steps must NOT be in response (deferred per CONTEXT.md)"
