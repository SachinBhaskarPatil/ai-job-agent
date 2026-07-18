"""Node: analyze a job description with GPT."""

from __future__ import annotations

import logging

from state import AgentState, JDAnalysis
from utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a recruiting analyst. Extract structured information from job descriptions.
Return ONLY valid JSON with these keys:
- skills (array of strings)
- technologies (array of strings)
- responsibilities (array of strings)
- years_of_experience (string, e.g. "3-5 years" or "Not specified")
"""


def analyze_jd_node(state: AgentState, *, openai_client: OpenAIClient) -> AgentState:
    """Use GPT to extract structured JD fields and store them in AgentState."""
    job_role = state.get("job_role", "")
    job_description = state.get("job_description", "")

    if not job_description.strip():
        return {"status": "failed", "error": "Job description is empty"}

    user_prompt = f"Job Role: {job_role}\n\nJob Description:\n{job_description}"

    try:
        result = openai_client.chat_json(SYSTEM_PROMPT, user_prompt)
        analysis: JDAnalysis = {
            "skills": list(result.get("skills", [])),
            "technologies": list(result.get("technologies", [])),
            "responsibilities": list(result.get("responsibilities", [])),
            "years_of_experience": str(result.get("years_of_experience", "Not specified")),
        }
        logger.info(
            "JD analyzed for '%s': %d skills, %d technologies",
            job_role,
            len(analysis["skills"]),
            len(analysis["technologies"]),
        )
        return {"jd_analysis": analysis, "status": "analyzed", "error": ""}
    except Exception as exc:
        logger.exception("analyze_jd_node failed for role '%s'", job_role)
        return {"status": "failed", "error": str(exc)}
