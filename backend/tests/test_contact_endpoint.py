"""Integration tests for POST /contact/submit endpoint.

Uses the shared `test_client` fixture (httpx AsyncClient backed by ASGI transport).
SMTP send is always intercepted — no real email delivery occurs.

Covers:
- Valid discuss submission → 200 with preview containing customer + CVE data
- Valid feature_request submission → 200
- Missing required field → 422
- Invalid CVE ID pattern → 422
- Invalid email address → 422
- Invalid context value → 422
- Email send failure (fire-and-forget) → HTTP 200 still returned
"""

from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Valid submissions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_discuss_returns_200(test_client, monkeypatch):
    """Valid discuss submission: HTTP 200, success=True, preview with customer + CVE data."""
    monkeypatch.setattr(
        "routes.contact._send_email_background",
        MagicMock(),
    )
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme Corp",
            "email": "jane@acme.com",
            "cve_id": "CVE-2024-1234",
            "context": "discuss",
            "testable": True,
            "cvss_score": 7.5,
            "attack_profiles": ["Strike-Alpha"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "preview" in body
    assert "Jane Doe" in body["preview"]
    assert "CVE-2024-1234" in body["preview"]


@pytest.mark.asyncio
async def test_submit_feature_request_returns_200(test_client, monkeypatch):
    """Valid feature_request submission: HTTP 200, success=True."""
    monkeypatch.setattr("routes.contact._send_email_background", MagicMock())
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Bob",
            "last_name": "Smith",
            "company": "Corp",
            "email": "bob@corp.com",
            "cve_id": "CVE-2025-9999",
            "context": "feature_request",
            "testable": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# Validation failures (422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_missing_email_returns_422(test_client):
    """Missing required field `email` must return 422 Unprocessable Entity."""
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            # email intentionally omitted
            "cve_id": "CVE-2024-1234",
            "context": "discuss",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_invalid_cve_id_returns_422(test_client):
    """CVE ID that does not match ^CVE-\\d{4}-\\d{1,7}$ must return 422."""
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "email": "jane@acme.com",
            "cve_id": "NOT-A-CVE-ID",
            "context": "discuss",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_invalid_email_returns_422(test_client):
    """Non-email string in `email` field must return 422."""
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "email": "not-an-email",
            "cve_id": "CVE-2024-1234",
            "context": "discuss",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_invalid_context_returns_422(test_client):
    """Context value outside Literal["discuss", "feature_request"] must return 422."""
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "email": "jane@acme.com",
            "cve_id": "CVE-2024-1234",
            "context": "invalid_value",
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Fire-and-forget: SMTP failure must NOT affect HTTP response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_returns_200_even_when_email_send_fails(test_client, monkeypatch):
    """BackgroundTask SMTP failure must not propagate to the HTTP response.

    _send_email_background wraps send_contact_email with a blanket try/except.
    Patching the underlying send_contact_email to raise verifies that:
      1. The endpoint returns HTTP 200 (response sent before background task runs).
      2. _send_email_background absorbs the exception — it never escapes to Starlette.
    """

    def failing_smtp(*args, **kwargs):
        raise Exception("SMTP connection refused")

    monkeypatch.setattr("routes.contact.send_contact_email", failing_smtp)

    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme",
            "email": "jane@acme.com",
            "cve_id": "CVE-2024-1234",
            "context": "discuss",
            "testable": True,
        },
    )
    # Response must be 200 regardless of background SMTP failure
    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# Response shape assertions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_response_contains_message(test_client, monkeypatch):
    """Response body must contain a `message` field."""
    monkeypatch.setattr("routes.contact._send_email_background", MagicMock())
    response = await test_client.post(
        "/contact/submit",
        json={
            "first_name": "Alice",
            "last_name": "Wong",
            "company": "SecureCorp",
            "email": "alice@securecorp.com",
            "cve_id": "CVE-2024-7777",
            "context": "discuss",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert isinstance(body["message"], str)
    assert len(body["message"]) > 0
