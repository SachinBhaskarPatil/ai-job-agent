"""Gmail API client for sending application emails."""

from __future__ import annotations

import base64
import logging
import mimetypes
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.errors import HttpError

from config import GmailConfig
from utils.gmail_auth import GmailAuthError, build_gmail_service

logger = logging.getLogger(__name__)


class GmailClientError(Exception):
    """Raised when a Gmail operation fails."""


class GmailClient:
    """Send emails with optional resume attachments via the Gmail API."""

    def __init__(self, config: GmailConfig) -> None:
        self._config = config
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        try:
            self._service = build_gmail_service(
                credentials_path=self._config.credentials_path,
                token_path=self._config.token_path,
            )
        except GmailAuthError as exc:
            raise GmailClientError(str(exc)) from exc

        return self._service

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        resume_path: Path | None = None,
    ) -> str:
        """Send an email and return the Gmail message ID."""
        if not to.strip():
            raise GmailClientError("Recipient email address is required")

        message = MIMEMultipart()
        message["to"] = to
        sender = self._config.sender_email
        if sender:
            message["from"] = sender
        else:
            logger.info("No sender configured; Gmail will use the authenticated account")
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if resume_path is not None:
            self._attach_file(message, resume_path)

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        payload = {"raw": encoded_message}

        try:
            service = self._get_service()
            result = (
                service.users()
                .messages()
                .send(userId="me", body=payload)
                .execute()
            )
            message_id = result.get("id", "")
            logger.info("Email sent to %s (message id: %s)", to, message_id)
            return message_id
        except HttpError as exc:
            logger.exception("Gmail API error while sending to %s", to)
            raise GmailClientError(f"Failed to send email to {to}") from exc

    @staticmethod
    def _attach_file(message: MIMEMultipart, file_path: Path) -> None:
        if not file_path.is_file():
            raise GmailClientError(f"Resume file not found: {file_path}")

        mime_type, _ = mimetypes.guess_type(str(file_path))
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)

        with file_path.open("rb") as file_handle:
            attachment = MIMEApplication(file_handle.read(), _subtype=subtype)
            attachment.add_header("Content-Disposition", "attachment", filename=file_path.name)
            message.attach(attachment)

        logger.info("Attached resume: %s", file_path.name)
