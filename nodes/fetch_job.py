"""Node: fetch one pending job from Google Sheets."""

from __future__ import annotations

import logging

from repositories.sheets_repository import SheetsRepository
from state import AgentState

logger = logging.getLogger(__name__)


def fetch_job_node(state: AgentState, *, repository: SheetsRepository) -> AgentState:
    """Read one Pending row and populate AgentState."""
    try:
        job = repository.get_one_pending_job()
        if job is None:
            logger.info("No pending jobs available")
            return {"status": "no_jobs"}

        logger.info("Fetched job: %s (row %d)", job.job_role, job.row_number)
        return {
            "row_number": job.row_number,
            "job_role": job.job_role,
            "job_description": job.job_description,
            "recruiter_email": job.recruiter_email,
            "email_type": job.email_type,
            "job_link": job.job_link,
            "status": "fetched",
            "error": "",
        }
    except Exception as exc:
        logger.exception("fetch_job_node failed")
        return {"status": "failed", "error": str(exc)}
