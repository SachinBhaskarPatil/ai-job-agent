"""Node: update Google Sheet status after processing."""

from __future__ import annotations

import logging

from repositories.sheets_repository import SheetsRepository
from state import AgentState

logger = logging.getLogger(__name__)


def update_sheet_node(state: AgentState, *, repository: SheetsRepository) -> AgentState:
    """Mark row as Sent or Failed with timestamp and optional error message."""
    row_number = state.get("row_number")
    if not row_number:
        logger.info("No row to update in sheet")
        return {}

    status = state.get("status", "")
    error = state.get("error", "")

    try:
        if status == "sent":
            repository.mark_sent(row_number)
            logger.info("Sheet updated: row %d -> Sent", row_number)
        elif status == "failed" or error:
            repository.mark_failed(row_number, error or "Unknown error")
            logger.info("Sheet updated: row %d -> Failed", row_number)
        else:
            logger.warning("Unexpected status '%s' for row %d; marking Failed", status, row_number)
            repository.mark_failed(row_number, f"Unexpected status: {status}")

        return {"status": "completed", "error": ""}
    except Exception as exc:
        logger.exception("update_sheet_node failed for row %d", row_number)
        return {"status": "failed", "error": str(exc)}
