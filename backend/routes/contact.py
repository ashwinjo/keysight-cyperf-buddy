"""Contact form router: POST /contact/submit.

Validates the inbound lead capture payload, renders the email body synchronously,
queues the SMTP send as a BackgroundTask (non-blocking), and returns the preview
immediately so the frontend can display confirmation to the user.

PII minimization: name and company are NOT logged. Only CVE ID, context, and
the submitter's email are written to the log.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr, Field

from config import Settings, get_settings
from services.email_service import (
    SMTPConfig,
    render_email_body,
    render_email_subject,
    send_contact_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contact", tags=["contact"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ContactFormRequest(BaseModel):
    """Validated payload for a contact form submission."""

    first_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    last_name: str = Field(..., min_length=1, max_length=100, strip_whitespace=True)
    company: str = Field(..., min_length=1, max_length=200, strip_whitespace=True)
    email: EmailStr
    cve_id: str = Field(..., pattern=r"^CVE-\d{4}-\d{1,7}$")
    context: Literal["discuss", "feature_request"]
    testable: bool = False
    cvss_score: float | None = None
    attack_profiles: list[str] = Field(default_factory=list)


class ContactFormResponse(BaseModel):
    """Response returned immediately after submission."""

    success: bool
    message: str
    preview: str  # Plain-text copy of the email body shown to the user


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def _get_smtp_config(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SMTPConfig:
    """Build an SMTPConfig from application settings.

    Injected via FastAPI Depends — no global state.
    """
    return SMTPConfig(
        server=settings.smtp_server,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        from_email=settings.smtp_from_email,
        recipient_email=settings.smtp_recipient_email,
    )


# ---------------------------------------------------------------------------
# Background task wrapper
# ---------------------------------------------------------------------------


def _send_email_background(
    to_email: str,
    subject: str,
    body: str,
    smtp_config: SMTPConfig,
) -> None:
    """Fire-and-forget email send wrapper.

    Catches all exceptions so the background task never crashes the worker.
    Failures are logged; the caller (endpoint) has already returned HTTP 200.
    """
    try:
        send_contact_email(to_email=to_email, subject=subject, body=body, smtp_config=smtp_config)
    except Exception as exc:
        logger.error(
            "Background email send failed to=%s: %s: %s",
            to_email,
            type(exc).__name__,
            exc,
        )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/submit", response_model=ContactFormResponse)
async def submit_contact_form(
    form_data: ContactFormRequest,
    background_tasks: BackgroundTasks,
    smtp_config: Annotated[SMTPConfig, Depends(_get_smtp_config)],
) -> ContactFormResponse:
    """Submit a sales funnel contact request.

    Validates the payload (422 on failure), renders the email body, queues the
    SMTP send as a background task, and returns the preview immediately.

    Returns HTTP 200 regardless of whether the email delivery succeeds — the
    send is fire-and-forget. Delivery failures are captured in server logs.
    """
    subject = render_email_subject(form_data.context, form_data.cve_id)
    body = render_email_body(
        first_name=form_data.first_name,
        last_name=form_data.last_name,
        company=form_data.company,
        customer_email=form_data.email,
        cve_id=form_data.cve_id,
        testable=form_data.testable,
        context=form_data.context,
        cvss_score=form_data.cvss_score,
        attack_profiles=form_data.attack_profiles,
    )

    background_tasks.add_task(
        _send_email_background,
        to_email=smtp_config.recipient_email,
        subject=subject,
        body=body,
        smtp_config=smtp_config,
    )

    # PII minimization: log only CVE ID, context, and submitter email — not name/company
    logger.info(
        "Contact form submitted cve=%s context=%s from=%s",
        form_data.cve_id,
        form_data.context,
        form_data.email,
    )

    return ContactFormResponse(
        success=True,
        message="Thank you. Your information has been sent.",
        preview=body,
    )
