"""Entry point for the AI Job Agent."""

from __future__ import annotations

import argparse
import logging
import sys

from config import get_settings
from graph import build_graph
from repositories.sheets_repository import SheetsRepository
from utils.gmail_client import GmailClient
from utils.openai_client import OpenAIClient
from utils.resume_reader import load_resume_text
from utils.sheets import GoogleSheetsClient, SheetsError


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


def print_sheets() -> int:
    """Step 1: connect to Google Sheets and print all rows."""
    settings = get_settings()
    sheets_config = settings.sheets

    client = GoogleSheetsClient(
        credentials_path=sheets_config.credentials_path,
        spreadsheet_id=sheets_config.spreadsheet_id,
        spreadsheet_name=sheets_config.spreadsheet_name,
        worksheet_name=sheets_config.worksheet_name,
    )

    try:
        client.print_all_rows()
        return 0
    except SheetsError as exc:
        logging.error("Google Sheets error: %s", exc)
        return 1


def run_agent() -> int:
    """Run the full LangGraph job-application pipeline."""
    settings = get_settings()
    sheets_config = settings.sheets

    sheets_client = GoogleSheetsClient(
        credentials_path=sheets_config.credentials_path,
        spreadsheet_id=sheets_config.spreadsheet_id,
        spreadsheet_name=sheets_config.spreadsheet_name,
        worksheet_name=sheets_config.worksheet_name,
    )
    repository = SheetsRepository(sheets_client)
    openai_client = OpenAIClient(settings.openai)
    gmail_client = GmailClient(settings.gmail)

    resume_text = load_resume_text(settings.agent.resume_path)

    graph = build_graph(
        repository=repository,
        openai_client=openai_client,
        gmail_client=gmail_client,
        resume_path=settings.agent.resume_path,
        resume_text=resume_text,
    )

    try:
        result = graph.invoke({})
        status = result.get("status", "unknown")
        if status == "no_jobs":
            logging.info("No pending jobs to process.")
            return 0
        if result.get("error"):
            logging.error("Pipeline finished with error: %s", result["error"])
            return 1
        logging.info("Pipeline completed successfully for row %s", result.get("row_number"))
        return 0
    except Exception:
        logging.exception("Pipeline execution failed")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Job Agent")
    parser.add_argument(
        "--print-sheets",
        action="store_true",
        help="Print all Google Sheet rows (Step 1 verification)",
    )
    args = parser.parse_args()

    settings = get_settings()
    _configure_logging(settings.agent.log_level)

    exit_code = print_sheets() if args.print_sheets else run_agent()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
