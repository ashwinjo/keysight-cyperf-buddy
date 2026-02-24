"""
End-to-end SMTP connectivity and email delivery test.

Only runs when SMTP_LIVE_TEST=true is set in the environment.
Requires SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
to be valid and reachable from the test environment.

Manual invocation:
    SMTP_LIVE_TEST=true pytest backend/tests/test_contact_e2e.py -v

In normal CI runs (no SMTP_LIVE_TEST), the test is SKIPPED — no email
is sent and no real credentials are required.
"""

import os

import pytest

from services.email_service import (
    SMTPConfig,
    render_email_body,
    render_email_subject,
    send_contact_email,
)

LIVE_TEST_ENABLED = os.environ.get("SMTP_LIVE_TEST", "false").lower() == "true"


@pytest.mark.skipif(not LIVE_TEST_ENABLED, reason="SMTP_LIVE_TEST not set")
def test_live_smtp_send() -> None:
    """Send a real email to the configured recipient.

    Run manually:
        SMTP_LIVE_TEST=true pytest backend/tests/test_contact_e2e.py -v

    Requires valid SMTP credentials in .env or environment variables:
        SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

    After the test passes, verify email receipt manually in
    ashwin.joshi@keysight.com inbox.
    """
    smtp_config = SMTPConfig(
        server=os.environ["SMTP_SERVER"],
        port=int(os.environ.get("SMTP_PORT", "587")),
        username=os.environ["SMTP_USERNAME"],
        password=os.environ["SMTP_PASSWORD"],
        from_email=os.environ.get("SMTP_FROM_EMAIL", os.environ["SMTP_USERNAME"]),
        recipient_email=os.environ.get("SMTP_RECIPIENT_EMAIL", "ashwin.joshi@keysight.com"),
    )

    subject = render_email_subject("discuss", "CVE-2024-1234")
    body = render_email_body(
        first_name="Test",
        last_name="User",
        company="Keysight E2E Test",
        customer_email="test@keysight.com",
        cve_id="CVE-2024-1234",
        testable=True,
        context="discuss",
        cvss_score=7.5,
        attack_profiles=["Strike-Test"],
    )

    # This will send a real email — confirm receipt manually
    send_contact_email(
        to_email=smtp_config.recipient_email,
        subject=f"[E2E TEST] {subject}",
        body=body,
        smtp_config=smtp_config,
    )
    # If we get here without exception, SMTP send succeeded.
    # Verify email was received manually in ashwin.joshi@keysight.com inbox.
