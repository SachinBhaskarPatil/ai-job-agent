"""Gmail OAuth authentication utility."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from config import PROJECT_ROOT

logger = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
DEFAULT_SCOPES = [GMAIL_SEND_SCOPE]

DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "gmail_credentials.json"
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "gmail_token.json"


class GmailAuthError(Exception):
    """Raised when Gmail OAuth authentication fails."""


def get_gmail_credentials(
    credentials_path: str | Path = DEFAULT_CREDENTIALS_PATH,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    scopes: list[str] | None = None,
) -> Credentials:
    """Load, refresh, or obtain Gmail OAuth credentials.

    Reuses ``gmail_token.json`` when present and valid. Refreshes expired
    tokens automatically. On first run, opens a browser for user sign-in and
    requests Gmail send permission.
    """
    creds_path = Path(credentials_path)
    token_file = Path(token_path)
    requested_scopes = scopes or DEFAULT_SCOPES

    creds: Credentials | None = None

    if token_file.is_file():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), requested_scopes)
            logger.info("Loaded Gmail token from %s", token_file)
        except (ValueError, OSError) as exc:
            logger.warning("Invalid Gmail token file; re-authorization required: %s", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing expired Gmail OAuth token")
            creds.refresh(Request())
            _save_token(creds, token_file)
            return creds
        except RefreshError as exc:
            logger.warning("Gmail token refresh failed; starting new OAuth flow: %s", exc)
            creds = None

    if not creds_path.is_file():
        raise GmailAuthError(f"Gmail credentials file not found: {creds_path}")

    try:
        logger.info("Starting Gmail OAuth flow (browser sign-in required)")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(creds_path),
            requested_scopes,
        )
        creds = flow.run_local_server(port=0)
    except (OSError, ValueError, GoogleAuthError) as exc:
        logger.exception("Gmail OAuth authorization failed")
        raise GmailAuthError("Gmail OAuth authorization failed") from exc

    _save_token(creds, token_file)
    return creds


def _save_token(creds: Credentials, token_path: Path) -> None:
    try:
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        logger.info("Gmail token saved to %s", token_path)
    except OSError as exc:
        logger.exception("Failed to save Gmail token to %s", token_path)
        raise GmailAuthError(f"Failed to save Gmail token to {token_path}") from exc


def build_gmail_service(
    credentials_path: str | Path = DEFAULT_CREDENTIALS_PATH,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    scopes: list[str] | None = None,
) -> Resource:
    """Return an authenticated Gmail API v1 service."""
    creds = get_gmail_credentials(credentials_path, token_path, scopes)
    try:
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.exception("Failed to build Gmail API client")
        raise GmailAuthError("Failed to build Gmail API client") from exc


def main() -> int:
    """Run one-time Gmail OAuth and save ``gmail_token.json``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    try:
        get_gmail_credentials()
        logger.info("Gmail authentication successful.")
        return 0
    except GmailAuthError as exc:
        logger.error("Gmail authentication failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
