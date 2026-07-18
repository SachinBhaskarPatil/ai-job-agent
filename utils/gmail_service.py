"""Production-ready Gmail API service for sending HTML emails."""

from __future__ import annotations

import base64
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

from config import get_settings
from utils.gmail_auth import GmailAuthError, build_gmail_service

logger = logging.getLogger(__name__)


class GmailService:
    """Send HTML emails with optional PDF attachments via the Gmail API."""

    def __init__(
        self,
        *,
        token_path: str | Path | None = None,
        credentials_path: str | Path | None = None,
        sender_email: str | None = None,
    ) -> None:
        settings = get_settings()
        self._token_path = Path(token_path or settings.gmail.token_path)
        self._credentials_path = Path(credentials_path or settings.gmail.credentials_path)
        self._sender_email = (sender_email or settings.gmail.sender_email).strip()
        self._service: Resource | None = None

    def _get_service(self) -> Resource:
        if self._service is not None:
            return self._service

        self._service = build_gmail_service(
            credentials_path=self._credentials_path,
            token_path=self._token_path,
        )
        return self._service

    def _resolve_sender_email(self) -> str | None:
        if self._sender_email:
            return self._sender_email

        # gmail.send scope does not allow profile lookup; omit From and let Gmail
        # use the authenticated OAuth account.
        logger.info("No sender configured; Gmail will use the authenticated account")
        return None

    @staticmethod
    def _build_message(
        *,
        sender: str | None,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachment_path: Path | None,
    ) -> MIMEMultipart:
        message = MIMEMultipart()
        message["to"] = recipient_email
        if sender:
            message["from"] = sender
        message["subject"] = subject
        message.attach(MIMEText(body_html, "html"))

        if attachment_path is not None:
            if not attachment_path.is_file():
                raise FileNotFoundError(f"Attachment not found: {attachment_path}")

            with attachment_path.open("rb") as file_handle:
                attachment = MIMEApplication(file_handle.read(), _subtype="pdf")
                attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment_path.name,
                )
                message.attach(attachment)
            logger.info("Attached PDF: %s", attachment_path.name)

        return message

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachment_path: Optional[str] = None,
    ) -> bool:
        """Send an HTML email and return True on success, False on failure."""
        recipient = recipient_email.strip()
        if not recipient:
            logger.error("Recipient email address is required")
            return False

        attachment = Path(attachment_path) if attachment_path else None

        try:
            service = self._get_service()
            sender = self._resolve_sender_email()
            message = self._build_message(
                sender=sender,
                recipient_email=recipient,
                subject=subject,
                body_html=body_html,
                attachment_path=attachment,
            )

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            result = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": encoded_message})
                .execute()
            )
            message_id = result.get("id", "")
            logger.info("Email sent to %s (message id: %s)", recipient, message_id)
            return True
        except (GmailAuthError, FileNotFoundError) as exc:
            logger.error("Failed to send email to %s: %s", recipient, exc)
            return False
        except HttpError:
            logger.exception("Gmail API error while sending to %s", recipient)
            return False
        except Exception:
            logger.exception("Unexpected error while sending email to %s", recipient)
            return False


_default_service: GmailService | None = None


def _get_default_service() -> GmailService:
    global _default_service
    if _default_service is None:
        _default_service = GmailService()
    return _default_service


def send_email(
    recipient_email: str,
    subject: str,
    body_html: str,
    attachment_path: Optional[str] = None,
) -> bool:
    """Send an HTML email via Gmail API. Returns True on success, False on failure."""
    return _get_default_service().send_email(
        recipient_email=recipient_email,
        subject=subject,
        body_html=body_html,
        attachment_path=attachment_path,
    )
