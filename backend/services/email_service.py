"""Email service: SMTP configuration, email rendering, and send logic.

Pure-function module with no FastAPI dependencies — fully testable in isolation.
All SMTP credentials are passed in as arguments; none are module-level globals.
Password is never logged in any code path.
"""

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPAuthenticationError, SMTPException

logger = logging.getLogger(__name__)

# Context label mapping used by both subject and body renderers
_CONTEXT_LABELS: dict[str, str] = {
    "discuss": "Let's Discuss",
    "feature_request": "Request Feature",
}


@dataclass
class SMTPConfig:
    """Typed container for SMTP connection parameters."""

    server: str
    port: int
    username: str
    password: str
    from_email: str
    recipient_email: str


def render_email_subject(context: str, cve_id: str) -> str:
    """Generate an email subject line based on contact context and CVE ID.

    Args:
        context: Contact context — "discuss" or "feature_request".
        cve_id: CVE identifier string (e.g., "CVE-2024-1234").

    Returns:
        Formatted subject line string.
    """
    if context == "discuss":
        return f"Customer Interest: {cve_id} Discussion"
    if context == "feature_request":
        return f"Feature Request: {cve_id}"

    # Defensive fallback — should not be reached if Pydantic Literal validation is upstream
    logger.warning(
        "render_email_subject received unknown context=%r for cve_id=%s; "
        "falling back to generic subject.",
        context,
        cve_id,
    )
    return f"CVE Inquiry: {cve_id}"


def render_email_body(
    first_name: str,
    last_name: str,
    company: str,
    customer_email: str,
    cve_id: str,
    testable: bool,
    context: str,
    cvss_score: float | None = None,
    attack_profiles: list[str] | None = None,
) -> str:
    """Render a plain-text email body from contact form fields.

    Args:
        first_name: Customer first name.
        last_name: Customer last name.
        company: Customer company name.
        customer_email: Customer email address.
        cve_id: CVE identifier string.
        testable: Whether the CVE is testable by Cyperf.
        context: Contact context — "discuss" or "feature_request".
        cvss_score: Optional CVSS v3.1 base score.
        attack_profiles: Optional list of Cyperf attack profile names.

    Returns:
        Plain-text email body string.
    """
    context_label = _CONTEXT_LABELS.get(context, context)
    testable_str = "Yes" if testable else "No"
    cvss_str = str(cvss_score) if cvss_score is not None else "N/A"

    profiles_list = attack_profiles or []
    profiles_str = ", ".join(profiles_list) if profiles_list else "None"

    return (
        f"Customer Contact: {context_label}\n"
        "\n"
        "Customer Information:\n"
        f"  Name: {first_name} {last_name}\n"
        f"  Company: {company}\n"
        f"  Email: {customer_email}\n"
        "\n"
        "CVE Details:\n"
        f"  CVE ID: {cve_id}\n"
        f"  Testable by Cyperf: {testable_str}\n"
        f"  CVSS v3.1: {cvss_str}\n"
        f"  Attack Profiles: {profiles_str}\n"
        "\n"
        f"Context: {context_label}\n"
        "\n"
        "---\n"
        "This contact was submitted via the Cyperf CVE Tracker.\n"
        "Please follow up with the customer to discuss their needs."
    )


def send_contact_email(
    to_email: str,
    subject: str,
    body: str,
    smtp_config: SMTPConfig,
    timeout: int = 10,
) -> None:
    """Send an email via SMTP with STARTTLS.

    Certificate validation is always enabled (ssl.create_default_context).
    The password is never logged.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        smtp_config: SMTP connection parameters.
        timeout: TCP connection timeout in seconds (default 10).

    Raises:
        SMTPAuthenticationError: On authentication failure.
        SMTPException: On any other SMTP-level failure.
        Exception: On any other unexpected error.
    """
    msg = MIMEMultipart()
    msg["From"] = smtp_config.from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    ssl_context = ssl.create_default_context()

    try:
        with smtplib.SMTP(smtp_config.server, smtp_config.port, timeout=timeout) as server:
            server.ehlo()
            server.starttls(context=ssl_context)
            server.ehlo()
            server.login(smtp_config.username, smtp_config.password)
            server.sendmail(smtp_config.from_email, to_email, msg.as_string())

        logger.info("Email sent to %s subject='%s'", to_email, subject)

    except SMTPAuthenticationError as exc:
        logger.error(
            "SMTP authentication failed for user=%s server=%s port=%d: %s",
            smtp_config.username,
            smtp_config.server,
            smtp_config.port,
            exc,
        )
        raise

    except SMTPException as exc:
        logger.error(
            "Email send failed to %s: %s: %s",
            to_email,
            type(exc).__name__,
            exc,
        )
        raise

    except Exception as exc:
        logger.error(
            "Email send failed to %s: %s: %s",
            to_email,
            type(exc).__name__,
            exc,
        )
        raise
