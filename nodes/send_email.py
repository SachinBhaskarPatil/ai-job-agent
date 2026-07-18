"""Node: send the application email via Gmail."""

from __future__ import annotations

import logging
from pathlib import Path

from state import AgentState
from utils.gmail_client import GmailClient

logger = logging.getLogger(__name__)


def send_email_node(
    state: AgentState,
    *,
    gmail_client: GmailClient,
    resume_path: Path,
) -> AgentState:
    """Send email with subject, body, and resume attachment."""
    recruiter_email = state.get("recruiter_email", "")
    subject = state.get("email_subject", "")
    body = state.get("email_body", "")

    if not recruiter_email.strip():
        return {"status": "failed", "error": "Recruiter email is missing"}

    try:
        message_id = gmail_client.send_email(
            to=recruiter_email,
            subject=subject,
            body=body,
            resume_path=resume_path if resume_path.is_file() else None,
        )
        logger.info("Application email sent (id: %s)", message_id)
        return {"status": "sent", "error": ""}
    except Exception as exc:
        logger.exception("send_email_node failed for %s", recruiter_email)
        return {"status": "failed", "error": str(exc)}
