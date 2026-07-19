"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class OpenAIConfig:
    """OpenAI API settings."""

    api_key: str
    model: str


@dataclass(frozen=True)
class GoogleSheetsConfig:
    """Google Sheets integration settings."""

    spreadsheet_id: str | None
    spreadsheet_name: str | None
    worksheet_name: str | None
    credentials_path: Path


@dataclass(frozen=True)
class GmailConfig:
    """Gmail API integration settings."""

    credentials_path: Path
    token_path: Path
    sender_email: str


@dataclass(frozen=True)
class AgentConfig:
    """Top-level agent runtime settings."""

    log_level: str
    resume_path: Path


@dataclass(frozen=True)
class Settings:
    """Aggregated application settings."""

    openai: OpenAIConfig
    sheets: GoogleSheetsConfig
    gmail: GmailConfig
    agent: AgentConfig


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_settings() -> Settings:
    """Build and return application settings from the environment."""
    credentials_path = Path(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", str(PROJECT_ROOT / "credentials.json"))
    )

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip() or None
    spreadsheet_name = os.getenv("GOOGLE_SHEET_NAME", "").strip() or None

    if not spreadsheet_id and not spreadsheet_name:
        spreadsheet_name = "AI Job Agent"

    return Settings(
        openai=OpenAIConfig(
            api_key=_require_env("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o",
        ),
        sheets=GoogleSheetsConfig(
            spreadsheet_id=spreadsheet_id,
            spreadsheet_name=spreadsheet_name,
            worksheet_name=os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "").strip() or None,
            credentials_path=credentials_path,
        ),
        gmail=GmailConfig(
            credentials_path=Path(
                os.getenv("GMAIL_CREDENTIALS_PATH", str(PROJECT_ROOT / "gmail_credentials.json"))
            ),
            token_path=Path(os.getenv("GMAIL_TOKEN_PATH", str(PROJECT_ROOT / "gmail_token.json"))),
            sender_email=os.getenv("GMAIL_SENDER_EMAIL", "").strip(),
        ),
        agent=AgentConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            resume_path=Path(os.getenv("RESUME_PATH", str(PROJECT_ROOT / "resumes" / "resume.pdf"))),
        ),
    )
