"""Shared test utilities (not fixtures — those go in conftest.py)."""


class DummyRateLimiter:
    """Test double for RateLimiter. Counts calls but never waits."""

    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1
