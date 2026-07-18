"""LangGraph workflow definition for the AI Job Agent."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from nodes.analyze_jd import analyze_jd_node
from nodes.fetch_job import fetch_job_node
from nodes.generate_email import generate_email_node
from nodes.send_email import send_email_node
from nodes.update_sheet import update_sheet_node
from repositories.sheets_repository import SheetsRepository
from state import AgentState
from utils.gmail_client import GmailClient
from utils.openai_client import OpenAIClient


def _route_after_fetch(state: AgentState) -> str:
    status = state.get("status", "")
    if status == "no_jobs":
        return END
    if status == "failed":
        return "update_sheet" if state.get("row_number") else END
    return "analyze_jd"


def _route_on_failure(state: AgentState, success_node: str) -> str:
    if state.get("status") == "failed":
        return "update_sheet"
    return success_node


def build_graph(
    repository: SheetsRepository,
    openai_client: OpenAIClient,
    gmail_client: GmailClient,
    resume_path: Path,
    resume_text: str = "",
) -> StateGraph:
    """Construct and return the compiled agent workflow graph."""
    workflow: StateGraph = StateGraph(AgentState)

    workflow.add_node(
        "fetch_job",
        partial(fetch_job_node, repository=repository),
    )
    workflow.add_node(
        "analyze_jd",
        partial(analyze_jd_node, openai_client=openai_client),
    )
    workflow.add_node(
        "generate_email",
        partial(generate_email_node, openai_client=openai_client, resume_text=resume_text),
    )
    workflow.add_node(
        "send_email",
        partial(
            send_email_node,
            gmail_client=gmail_client,
            resume_path=resume_path,
        ),
    )
    workflow.add_node(
        "update_sheet",
        partial(update_sheet_node, repository=repository),
    )

    workflow.add_edge(START, "fetch_job")
    workflow.add_conditional_edges(
        "fetch_job",
        _route_after_fetch,
        {
            "analyze_jd": "analyze_jd",
            "update_sheet": "update_sheet",
            END: END,
        },
    )
    workflow.add_conditional_edges(
        "analyze_jd",
        lambda state: _route_on_failure(state, "generate_email"),
        {
            "generate_email": "generate_email",
            "update_sheet": "update_sheet",
        },
    )
    workflow.add_conditional_edges(
        "generate_email",
        lambda state: _route_on_failure(state, "send_email"),
        {
            "send_email": "send_email",
            "update_sheet": "update_sheet",
        },
    )
    workflow.add_edge("send_email", "update_sheet")
    workflow.add_edge("update_sheet", END)

    return workflow.compile()
