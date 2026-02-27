"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_tags() -> list[str]:
    """Sample tag list for testing."""
    return ["1girl", "solo", "long hair", "blue eyes", "smile"]
