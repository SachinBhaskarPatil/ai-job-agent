"""Shared pytest fixtures."""

import pytest


@pytest.fixture
def sample_job() -> dict:
    """Minimal job record for testing."""
    return {
        "id": "job-001",
        "title": "Software Engineer",
        "company": "Example Corp",
        "url": "https://example.com/jobs/001",
        "description": "Placeholder job description.",
        "status": "pending",
    }
