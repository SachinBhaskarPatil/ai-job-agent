"""Tests for SheetsRepository."""

from unittest.mock import MagicMock

import pytest

from repositories.sheets_repository import (
    HEADER_JOB_DESCRIPTION,
    HEADER_JOB_ROLE,
    HEADER_RECRUITER_EMAIL,
    HEADER_STATUS,
    SheetsRepository,
    STATUS_PENDING,
)


@pytest.fixture
def sample_rows() -> list[list[str]]:
    return [
        [HEADER_JOB_ROLE, HEADER_JOB_DESCRIPTION, HEADER_RECRUITER_EMAIL, HEADER_STATUS],
        ["Engineer", "Build APIs", "hr@example.com", STATUS_PENDING],
        ["Designer", "Design UI", "design@example.com", "Sent"],
    ]


def test_get_one_pending_job_returns_first_pending(sample_rows: list[list[str]]) -> None:
    client = MagicMock()
    client.get_all_rows.return_value = sample_rows
    repo = SheetsRepository(client)

    job = repo.get_one_pending_job()

    assert job is not None
    assert job.row_number == 2
    assert job.job_role == "Engineer"
    assert job.job_description == "Build APIs"
    assert job.recruiter_email == "hr@example.com"


def test_get_one_pending_job_returns_none_when_empty() -> None:
    client = MagicMock()
    client.get_all_rows.return_value = [
        [HEADER_JOB_ROLE, HEADER_JOB_DESCRIPTION, HEADER_RECRUITER_EMAIL, HEADER_STATUS],
    ]
    repo = SheetsRepository(client)

    assert repo.get_one_pending_job() is None
