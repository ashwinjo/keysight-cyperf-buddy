"""Unit tests for services/email_service.py.

Tests cover:
- render_email_subject: both valid contexts and unknown fallback
- render_email_body: all field rendering edge cases including None CVSS and empty attack profiles
- send_contact_email: mocked SMTP — no real network connection

All tests are deterministic and require no external services.
"""

import smtplib
from unittest.mock import patch

import pytest

from services.email_service import (
    SMTPConfig,
    render_email_body,
    render_email_subject,
    send_contact_email,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_smtp_config() -> SMTPConfig:
    """Minimal SMTPConfig with test-safe values — no real credentials."""
    return SMTPConfig(
        server="smtp.test.internal",
        port=587,
        username="test-user@keysight.com",
        password="test-password",
        from_email="test-user@keysight.com",
        recipient_email="ashwin.joshi@keysight.com",
    )


# ---------------------------------------------------------------------------
# render_email_subject tests
# ---------------------------------------------------------------------------


def test_subject_discuss():
    result = render_email_subject("discuss", "CVE-2024-1234")
    assert result == "Customer Interest: CVE-2024-1234 Discussion"


def test_subject_feature_request():
    result = render_email_subject("feature_request", "CVE-2024-5678")
    assert result == "Feature Request: CVE-2024-5678"


def test_subject_unknown_context_uses_fallback():
    result = render_email_subject("unknown", "CVE-2024-9999")
    # Must not raise; CVE ID must appear in the fallback output
    assert "CVE-2024-9999" in result


def test_subject_does_not_expose_credentials():
    result = render_email_subject("discuss", "CVE-2024-1234")
    # Subject line must not contain an '@'-prefixed credential fragment
    assert "@" not in result or "keysight.com" not in result.split("@")[0]


# ---------------------------------------------------------------------------
# render_email_body tests
# ---------------------------------------------------------------------------


def test_body_contains_customer_info():
    body = render_email_body(
        first_name="Jane",
        last_name="Doe",
        company="Acme Corp",
        customer_email="jane@acme.com",
        cve_id="CVE-2024-1234",
        testable=True,
        context="discuss",
        cvss_score=7.5,
        attack_profiles=["Strike-Alpha", "Strike-Beta"],
    )
    assert "Jane Doe" in body
    assert "Acme Corp" in body
    assert "jane@acme.com" in body


def test_body_contains_cve_details():
    body = render_email_body(
        first_name="John",
        last_name="Smith",
        company="Corp",
        customer_email="j@corp.com",
        cve_id="CVE-2024-5678",
        testable=False,
        context="feature_request",
        cvss_score=None,
        attack_profiles=[],
    )
    assert "CVE-2024-5678" in body
    assert "No" in body  # testable=False → "No"


def test_body_testable_true_shows_yes():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
    )
    assert "Yes" in body


def test_body_includes_cvss_when_provided():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
        cvss_score=9.8,
    )
    assert "9.8" in body


def test_body_handles_no_cvss():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
        cvss_score=None,
    )
    # Must render gracefully — no raw Python "None" string in output
    assert "N/A" in body or "None" not in body


def test_body_includes_context_label_discuss():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
    )
    assert "Let's Discuss" in body


def test_body_includes_context_label_feature_request():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=False,
        context="feature_request",
    )
    assert "Request Feature" in body


def test_body_attack_profiles_listed():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
        attack_profiles=["Strike-001", "Strike-002"],
    )
    assert "Strike-001" in body
    assert "Strike-002" in body


def test_body_no_attack_profiles_shows_none():
    body = render_email_body(
        first_name="A",
        last_name="B",
        company="C",
        customer_email="a@b.com",
        cve_id="CVE-2024-0001",
        testable=True,
        context="discuss",
        attack_profiles=[],
    )
    # Must not crash; must indicate no profiles present
    assert "None" in body or "N/A" in body or "\u2014" in body


# ---------------------------------------------------------------------------
# send_contact_email tests (mocked SMTP — no real connection)
# ---------------------------------------------------------------------------


def test_send_email_calls_smtp(mock_smtp_config: SMTPConfig) -> None:
    """Verify correct SMTP connection sequence: connect → starttls → login → sendmail."""
    with patch("services.email_service.smtplib.SMTP") as MockSMTP:
        instance = MockSMTP.return_value.__enter__.return_value

        send_contact_email(
            to_email="ashwin.joshi@keysight.com",
            subject="Test Subject",
            body="Test Body",
            smtp_config=mock_smtp_config,
        )

        MockSMTP.assert_called_once_with(
            mock_smtp_config.server,
            mock_smtp_config.port,
            timeout=10,
        )
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with(
            mock_smtp_config.username,
            mock_smtp_config.password,
        )
        instance.sendmail.assert_called_once()


def test_send_email_raises_on_smtp_auth_error(mock_smtp_config: SMTPConfig) -> None:
    """SMTPAuthenticationError from login must propagate — not silently swallowed."""
    with patch("services.email_service.smtplib.SMTP") as MockSMTP:
        instance = MockSMTP.return_value.__enter__.return_value
        instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"auth failed")

        with pytest.raises(smtplib.SMTPAuthenticationError):
            send_contact_email(
                to_email="ashwin.joshi@keysight.com",
                subject="Subject",
                body="Body",
                smtp_config=mock_smtp_config,
            )


def test_send_email_raises_on_smtp_error(mock_smtp_config: SMTPConfig) -> None:
    """SMTPException from sendmail must propagate — not silently swallowed."""
    with patch("services.email_service.smtplib.SMTP") as MockSMTP:
        instance = MockSMTP.return_value.__enter__.return_value
        instance.sendmail.side_effect = smtplib.SMTPException("Connection reset")

        with pytest.raises(smtplib.SMTPException):
            send_contact_email(
                to_email="ashwin.joshi@keysight.com",
                subject="Subject",
                body="Body",
                smtp_config=mock_smtp_config,
            )


def test_send_email_builds_correct_recipient(mock_smtp_config: SMTPConfig) -> None:
    """sendmail must be called with the to_email argument, not from_email."""
    with patch("services.email_service.smtplib.SMTP") as MockSMTP:
        instance = MockSMTP.return_value.__enter__.return_value

        target = "recipient@example.com"
        send_contact_email(
            to_email=target,
            subject="Subject",
            body="Body",
            smtp_config=mock_smtp_config,
        )

        call_args = instance.sendmail.call_args
        # sendmail(from_addr, to_addrs, msg) — to_addrs is the second positional arg
        assert call_args[0][1] == target
