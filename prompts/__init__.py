"""Prompt templates for the AI Job Agent."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


def load_prompt(name: str) -> str:
    """Load a prompt template by filename (without extension)."""
    raise NotImplementedError
