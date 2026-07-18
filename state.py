"""LangGraph state definitions for the AI Job Agent."""

from typing import TypedDict


class JDAnalysis(TypedDict, total=False):
    """Structured job-description analysis returned by GPT."""

    skills: list[str]
    technologies: list[str]
    responsibilities: list[str]
    years_of_experience: str


class AgentState(TypedDict, total=False):
    """Shared state passed between graph nodes."""

    row_number: int
    job_role: str
    job_description: str
    recruiter_email: str
    email_type: str
    job_link: str
    email_subject: str
    email_body: str
    status: str
    error: str
    jd_analysis: JDAnalysis
