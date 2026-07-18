"""Manual integration test: send a real email via the Gmail API."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone

from config import get_settings
from utils.gmail_service import send_email

RECIPIENT = "sachinpatil.developer@gmail.com"


def main() -> int:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.agent.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    resume_path = settings.agent.resume_path
    attachment = str(resume_path) if resume_path.is_file() else None

    body_html = f"""
    <html>
      <body>
        <h2>AI Job Agent — Gmail Integration Test</h2>
        <p>This is a test email sent via the <strong>Gmail API</strong>.</p>
        <p>Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}</p>
        <p>If you received this message, Gmail integration is working.</p>
      </body>
    </html>
    """

    success = send_email(
        recipient_email=RECIPIENT,
        subject="AI Job Agent — Gmail Test",
        body_html=body_html,
        attachment_path=attachment,
    )

    if success:
        logging.info("Test email sent successfully to %s", RECIPIENT)
        return 0

    logging.error("Failed to send test email to %s", RECIPIENT)
    return 1


if __name__ == "__main__":
    sys.exit(main())
