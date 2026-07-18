"""Production-ready Google Sheets client using gspread."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, GSpreadException, SpreadsheetNotFound, WorksheetNotFound

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsError(Exception):
    """Raised when a Google Sheets operation fails."""


class GoogleSheetsClient:
    """Reusable gspread wrapper for reading and updating spreadsheets."""

    def __init__(
        self,
        credentials_path: str | Path,
        spreadsheet_id: str | None = None,
        spreadsheet_name: str | None = None,
        worksheet_name: str | None = None,
    ) -> None:
        self._credentials_path = Path(credentials_path)
        self._spreadsheet_id = spreadsheet_id
        self._spreadsheet_name = spreadsheet_name
        self._worksheet_name = worksheet_name
        self._client: gspread.Client | None = None
        self._worksheet: gspread.Worksheet | None = None

    def _authorize(self) -> gspread.Client:
        if self._client is not None:
            return self._client

        if not self._credentials_path.is_file():
            raise SheetsError(f"Credentials file not found: {self._credentials_path}")

        try:
            credentials = Credentials.from_service_account_file(
                str(self._credentials_path),
                scopes=SCOPES,
            )
            self._client = gspread.authorize(credentials)
            logger.info("Authenticated with Google Sheets API")
            return self._client
        except (OSError, ValueError) as exc:
            logger.exception("Failed to load service account credentials")
            raise SheetsError("Invalid credentials file") from exc
        except GSpreadException as exc:
            logger.exception("gspread authorization failed")
            raise SheetsError("Google Sheets authorization failed") from exc

    def _get_worksheet(self) -> gspread.Worksheet:
        if self._worksheet is not None:
            return self._worksheet

        client = self._authorize()

        try:
            if self._spreadsheet_id:
                spreadsheet = client.open_by_key(self._spreadsheet_id)
            elif self._spreadsheet_name:
                spreadsheet = client.open(self._spreadsheet_name)
            else:
                raise SheetsError("Either spreadsheet_id or spreadsheet_name must be provided")

            if self._worksheet_name:
                self._worksheet = spreadsheet.worksheet(self._worksheet_name)
            else:
                self._worksheet = spreadsheet.sheet1

            logger.info(
                "Opened worksheet '%s' in spreadsheet '%s'",
                self._worksheet.title,
                spreadsheet.title,
            )
            return self._worksheet
        except SpreadsheetNotFound as exc:
            logger.error("Spreadsheet not found")
            raise SheetsError("Spreadsheet not found") from exc
        except WorksheetNotFound as exc:
            logger.error("Worksheet not found: %s", self._worksheet_name)
            raise SheetsError(f"Worksheet not found: {self._worksheet_name}") from exc
        except GSpreadException as exc:
            logger.exception("Failed to open spreadsheet")
            raise SheetsError("Failed to open spreadsheet") from exc

    def get_all_rows(self) -> list[list[str]]:
        """Return every row in the worksheet (including the header row)."""
        try:
            worksheet = self._get_worksheet()
            rows = worksheet.get_all_values()
            logger.info("Fetched %d row(s) from Google Sheet", len(rows))
            return rows
        except APIError as exc:
            logger.exception("Google Sheets API error while reading rows")
            raise SheetsError("Failed to read rows from Google Sheet") from exc

    def get_records(self) -> list[dict[str, str]]:
        """Return all data rows as dictionaries keyed by header names."""
        rows = self.get_all_rows()
        if not rows:
            return []

        headers = [header.strip() for header in rows[0]]
        records: list[dict[str, str]] = []

        for row in rows[1:]:
            record = {
                headers[index]: (row[index] if index < len(row) else "")
                for index in range(len(headers))
            }
            records.append(record)

        return records

    def update_row_cells(self, row_number: int, updates: dict[str, Any]) -> None:
        """Update specific columns on a row using header names."""
        try:
            worksheet = self._get_worksheet()
            headers = worksheet.row_values(1)

            for column_name, value in updates.items():
                if column_name not in headers:
                    logger.warning("Column '%s' not found in sheet; skipping", column_name)
                    continue
                col_index = headers.index(column_name) + 1
                worksheet.update_cell(row_number, col_index, value)

            logger.info("Updated row %d: %s", row_number, list(updates.keys()))
        except APIError as exc:
            logger.exception("Google Sheets API error while updating row %d", row_number)
            raise SheetsError(f"Failed to update row {row_number}") from exc

    def print_all_rows(self) -> None:
        """Read and print every row in the worksheet."""
        rows = self.get_all_rows()
        if not rows:
            print("No rows found in the Google Sheet.")
            return

        for row in rows:
            print("\t".join(row))
