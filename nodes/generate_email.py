"""Node: generate a professional outreach email with GPT.

Supports two email types:
- "job": an application email sent directly to a recruiter.
- "referral": a polite request asking a contact at the company to refer the
  candidate, including the job link/ID and role details.
"""

from __future__ import annotations

import logging
import re

from state import AgentState
from utils.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

EMAIL_TYPE_JOB = "job"
EMAIL_TYPE_REFERRAL = "referral"

JOB_GREETING_NAME = "Hiring Manager"
REFERRAL_GREETING = "Hello"

JOB_SYSTEM_PROMPT = """You are the job applicant writing a warm, professional outreach email to a recruiter.
The email must read like it was written by a real person, not by AI.

Return ONLY valid JSON with these keys:
- subject (string, specific and professional; mention the role)
- body (string, the full email body)

Length & structure:
- Medium length: roughly 120-160 words, 3 short paragraphs.
- Paragraph 1: greeting + which role you're applying for + a genuine hook.
- Paragraph 2: 2-3 concrete achievements/skills from the resume that match the job.
- Paragraph 3: brief, confident close + thanks, then a sign-off.

Greeting rule:
- Start with "Dear Hiring Manager," unless an actual recruiter name is given in the input.
- NEVER use bracketed placeholders such as [Recruiter's Name], [Company], or [Your Name].

Tone & honesty:
- First person, AS the candidate. Natural, human, conversational-but-professional.
- Vary sentence length; avoid robotic or buzzword-heavy phrasing.
- Use ONLY facts from the candidate's resume. Do not invent employers, titles, or experience.
- If the resume lacks a required skill, lean on genuine adjacent strengths instead of fabricating.
- End with a sign-off using the candidate's real name from the resume.
"""

REFERRAL_SYSTEM_PROMPT = """You are the candidate writing a warm, polite email asking someone who works at the target company to REFER you for a specific role.
The email must read like it was written by a real person, not by AI.

Return ONLY valid JSON with these keys:
- subject (string; make it clearly a referral request that mentions the role)
- body (string, the full email body)

Length & structure:
- Medium length: roughly 120-170 words, 3 short paragraphs.
- Paragraph 1: friendly greeting + politely explain you're reaching out to ask for a referral for the specific role at their company.
- Paragraph 2: 2-3 concrete, relevant achievements/skills from the resume that make you a strong fit.
- Paragraph 3: include the job link or job ID if provided, make the ask easy and low-pressure, thank them sincerely, then sign off.

Greeting rule:
- Start with "Hello," unless an actual contact name is given in the input.
- NEVER use bracketed placeholders such as [Name], [Company], or [Your Name].

Tone & honesty:
- First person, AS the candidate. Humble, appreciative, and respectful of their time.
- Do NOT be pushy or entitled; a referral is a favor.
- Vary sentence length; avoid robotic or buzzword-heavy phrasing.
- Use ONLY facts from the candidate's resume. Do not invent employers, titles, or experience.
- If a job link or job ID is provided, include it clearly so they can find the posting.
- End with a sign-off using the candidate's real name from the resume.
"""

_PLACEHOLDER_RE = re.compile(r"\[[^\]]*\]")
_GREETING_PLACEHOLDER_RE = re.compile(r"(?im)^\s*(dear|hi|hello)\b[^\n,]*\[[^\]]*\][^\n]*")


def _sanitize_body(body: str, default_greeting: str) -> str:
    """Replace leftover bracketed placeholders and fix a placeholder greeting."""
    body = _GREETING_PLACEHOLDER_RE.sub(default_greeting, body, count=1)
    body = _PLACEHOLDER_RE.sub("", body)
    lines = [line.rstrip() for line in body.splitlines()]
    cleaned = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _format_analysis(state: AgentState) -> str:
    analysis = state.get("jd_analysis") or {}
    if not analysis:
        return ""

    parts = []
    if analysis.get("skills"):
        parts.append("Key skills: " + ", ".join(analysis["skills"]))
    if analysis.get("technologies"):
        parts.append("Technologies: " + ", ".join(analysis["technologies"]))
    if analysis.get("years_of_experience"):
        parts.append("Experience required: " + str(analysis["years_of_experience"]))
    return "\n".join(parts)


def generate_email_node(
    state: AgentState,
    *,
    openai_client: OpenAIClient,
    resume_text: str = "",
) -> AgentState:
    """Generate a personalized job-application or referral-request email."""
    job_role = state.get("job_role", "")
    job_description = state.get("job_description", "")
    email_type = (state.get("email_type") or EMAIL_TYPE_JOB).strip().lower()
    job_link = (state.get("job_link") or "").strip()

    if not job_role.strip():
        return {"status": "failed", "error": "Job role is missing"}

    is_referral = email_type == EMAIL_TYPE_REFERRAL
    system_prompt = REFERRAL_SYSTEM_PROMPT if is_referral else JOB_SYSTEM_PROMPT
    default_greeting = f"{REFERRAL_GREETING}," if is_referral else f"Dear {JOB_GREETING_NAME},"

    resume_section = (
        resume_text.strip()
        if resume_text.strip()
        else "(No resume provided — write a professional but general email without inventing details.)"
    )
    analysis_section = _format_analysis(state)

    user_prompt = (
        f"CANDIDATE RESUME:\n{resume_section}\n\n"
        f"----\n"
        f"TARGET ROLE: {job_role}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n"
    )
    if job_link:
        user_prompt += f"\nJOB LINK / JOB ID: {job_link}\n"
    if analysis_section:
        user_prompt += f"\nJOB REQUIREMENTS SUMMARY:\n{analysis_section}\n"

    try:
        result = openai_client.chat_json(system_prompt, user_prompt)
        subject = str(result.get("subject", "")).strip()
        body = _sanitize_body(str(result.get("body", "")).strip(), default_greeting)

        if not subject or not body:
            raise ValueError("GPT returned empty subject or body")

        word_count = len(body.split())
        if word_count > 220:
            logger.warning("Generated email exceeds 220 words (%d); truncating", word_count)
            body = " ".join(body.split()[:220])

        logger.info(
            "Generated %s email for '%s' (%d words)", email_type, job_role, len(body.split())
        )
        return {
            "email_subject": subject,
            "email_body": body,
            "status": "email_generated",
            "error": "",
        }
    except Exception as exc:
        logger.exception("generate_email_node failed for role '%s'", job_role)
        return {"status": "failed", "error": str(exc)}
