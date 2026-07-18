"""Google Sheets repository — read/write job application rows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from utils.sheets import GoogleSheetsClient, SheetsError

logger = logging.getLogger(__name__)

STATUS_PENDING = "Pending"
STATUS_SENT = "Sent"
STATUS_FAILED = "Failed"

EMAIL_TYPE_JOB = "job"
EMAIL_TYPE_REFERRAL = "referral"

HEADER_JOB_ROLE = "Job Role"
HEADER_JOB_DESCRIPTION = "Job Description"
HEADER_RECRUITER_EMAIL = "Recruiter Email"
HEADER_STATUS = "Status"
HEADER_TIMESTAMP = "Timestamp"
HEADER_ERROR = "Error"
HEADER_EMAIL_TYPE = "Email Type"
HEADER_JOB_LINK = "Job Link"


@dataclass(frozen=True)
class PendingJob:
    """A single pending job row from the spreadsheet."""

    row_number: int
    job_role: str
    job_description: str
    recruiter_email: str
    email_type: str = EMAIL_TYPE_JOB
    job_link: str = ""


class SheetsRepository:
    """Repository for job rows stored in Google Sheets."""

    def __init__(self, client: GoogleSheetsClient) -> None:
        self._client = client

    def get_one_pending_job(self) -> PendingJob | None:
        """Return the first row where Status == Pending, or None if none exist."""
        try:
            rows = self._client.get_all_rows()
        except SheetsError:
            logger.exception("Failed to fetch rows for pending job lookup")
            raise

        if len(rows) < 2:
            logger.info("No data rows found in spreadsheet")
            return None

        headers = [header.strip() for header in rows[0]]
        status_col = self._column_index(headers, HEADER_STATUS)
        role_col = self._column_index(headers, HEADER_JOB_ROLE)
        description_col = self._column_index(headers, HEADER_JOB_DESCRIPTION)
        email_col = self._column_index(headers, HEADER_RECRUITER_EMAIL)
        email_type_col = self._optional_column_index(headers, HEADER_EMAIL_TYPE)
        job_link_col = self._optional_column_index(headers, HEADER_JOB_LINK)

        for row_index, row in enumerate(rows[1:], start=2):
            status = self._cell_value(row, status_col)
            if status.strip().lower() != STATUS_PENDING.lower():
                continue

            job = PendingJob(
                row_number=row_index,
                job_role=self._cell_value(row, role_col),
                job_description=self._cell_value(row, description_col),
                recruiter_email=self._cell_value(row, email_col),
                email_type=self._normalize_email_type(
                    self._cell_value(row, email_type_col) if email_type_col is not None else ""
                ),
                job_link=(
                    self._cell_value(row, job_link_col).strip()
                    if job_link_col is not None
                    else ""
                ),
            )
            logger.info(
                "Found pending job at row %d: %s (type: %s)",
                job.row_number,
                job.job_role,
                job.email_type,
            )
            return job

        logger.info("No pending jobs found")
        return None

    def mark_sent(self, row_number: int) -> None:
        """Update status to Sent and record the current timestamp."""
        self._update_status(row_number, STATUS_SENT)

    def mark_failed(self, row_number: int, error_message: str) -> None:
        """Update status to Failed, store the error, and record the timestamp."""
        self._update_status(
            row_number,
            STATUS_FAILED,
            extra={HEADER_ERROR: error_message},
        )

    def _update_status(
        self,
        row_number: int,
        status: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        updates: dict[str, Any] = {
            HEADER_STATUS: status,
            HEADER_TIMESTAMP: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        if extra:
            updates.update(extra)

        self._client.update_row_cells(row_number, updates)
        logger.info("Row %d marked as %s", row_number, status)

    @staticmethod
    def _column_index(headers: list[str], column_name: str) -> int:
        normalized = {header.strip().lower(): index for index, header in enumerate(headers)}
        key = column_name.strip().lower()
        if key not in normalized:
            raise SheetsError(f"Required column '{column_name}' not found in spreadsheet headers")
        return normalized[key]

    @staticmethod
    def _optional_column_index(headers: list[str], column_name: str) -> int | None:
        normalized = {header.strip().lower(): index for index, header in enumerate(headers)}
        return normalized.get(column_name.strip().lower())

    @staticmethod
    def _normalize_email_type(value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {EMAIL_TYPE_REFERRAL, "refer", "referral email"}:
            return EMAIL_TYPE_REFERRAL
        return EMAIL_TYPE_JOB

    @staticmethod
    def _cell_value(row: list[str], column_index: int) -> str:
        if column_index >= len(row):
            return ""
        return row[column_index]
