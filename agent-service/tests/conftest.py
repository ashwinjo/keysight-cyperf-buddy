import sys
import types
import pytest
import os
from unittest.mock import MagicMock

# Set GEMINI_API_KEY before any imports that trigger config loading
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-tests")
os.environ.setdefault("BACKEND_API_URL", "http://localhost:8000")

# Stub google.generativeai before any test module imports it.
# google-generativeai 0.7.0 has a protobuf C-extension incompatibility with
# Python 3.14. Patching via sys.modules makes it importable in the test
# environment while all real Gemini calls are mocked per test.
if "google.generativeai" not in sys.modules:
    _genai_stub = MagicMock()
    _genai_stub.GenerativeModel = MagicMock
    _genai_stub.configure = MagicMock()
    sys.modules["google.generativeai"] = _genai_stub
    # Ensure the parent namespace exists too
    if "google" not in sys.modules:
        _google_stub = types.ModuleType("google")
        _google_stub.generativeai = _genai_stub  # type: ignore[attr-defined]
        sys.modules["google"] = _google_stub


@pytest.fixture
def sample_apps() -> list[dict]:
    return [
        {
            "name": "HTTP Traffic",
            "description": "HTTP/1.1 and HTTP/2 application traffic simulation",
        },
        {
            "name": "Video Streaming",
            "description": "HLS and DASH video streaming with QoE metrics",
        },
        {
            "name": "DNS Query Load",
            "description": "High volume DNS query traffic generator",
        },
    ]


@pytest.fixture
def sample_strikes() -> list[dict]:
    return [
        {"strike_name": "DDoS_Volumetric_UDP_Flood"},
        {"strike_name": "HTTP_Slowloris_Attack"},
        {"strike_name": "DNS_Amplification_Attack"},
    ]


@pytest.fixture
def sample_request_app() -> dict:
    return {
        "testing_focus": "app_performance",
        "use_case": "Measure HTTP load balancer performance under high concurrency",
        "objectives": "Achieve 10k concurrent connections with sub-200ms latency",
        "timeline": "2 weeks before production rollout",
    }


@pytest.fixture
def sample_request_security() -> dict:
    return {
        "testing_focus": "security_attacks",
        "use_case": "Validate firewall resilience against DDoS volumetric attacks",
        "objectives": "Sustain 10Gbps attack traffic with zero packet loss on backend",
        "timeline": "1 week security audit",
    }


@pytest.fixture
def sample_request_both() -> dict:
    return {
        "testing_focus": "both",
        "use_case": "Full L4-7 stack validation before go-live",
        "objectives": "Performance baseline and security posture verification",
        "timeline": "3 weeks sprint",
    }
