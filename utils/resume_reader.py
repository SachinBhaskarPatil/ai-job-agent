"""Read resume content from PDF or plain-text files for email personalization."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TEXT_SUFFIXES = {".txt", ".md"}


def load_resume_text(resume_path: str | Path, max_chars: int = 8000) -> str:
    """Return the resume's text content, or an empty string if unavailable.

    Supports PDF (parsed via pypdf) and plain-text (.txt/.md) files. Never
    raises for a missing or unreadable file; instead logs and returns "" so the
    email pipeline can degrade gracefully.
    """
    path = Path(resume_path)

    if not path.is_file():
        logger.warning("Resume file not found: %s (emails will be generic)", path)
        return ""

    suffix = path.suffix.lower()

    try:
        if suffix == ".pdf":
            text = _read_pdf(path)
        elif suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            logger.warning("Unsupported resume format '%s'; skipping", suffix)
            return ""
    except Exception:
        logger.exception("Failed to read resume: %s", path)
        return ""

    text = _normalize(text)
    if not text:
        logger.warning("Resume file '%s' produced no readable text", path)
        return ""

    if len(text) > max_chars:
        logger.info("Resume text truncated from %d to %d chars", len(text), max_chars)
        text = text[:max_chars]

    logger.info("Loaded resume text from %s (%d chars)", path.name, len(text))
    return text


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _normalize(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()
