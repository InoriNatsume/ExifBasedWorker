"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_tags() -> list[str]:
    """Sample tag list for testing."""
    return ["1girl", "solo", "long hair", "blue eyes", "smile"]
