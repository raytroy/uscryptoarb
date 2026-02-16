import json
from pathlib import Path

"""Shared test utilities (not fixtures — those go in conftest.py)."""


class DummyRateLimiter:
    """Test double for RateLimiter. Counts calls but never waits."""

    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file from tests/fixtures/.

    Centralized helper replacing per-module copies in parser test files.
    """
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)
