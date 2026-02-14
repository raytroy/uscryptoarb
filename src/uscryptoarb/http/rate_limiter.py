from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable


class RateLimiter:
    """Enforces minimum interval between requests to an exchange."""

    def __init__(
        self,
        min_interval_ms: int = 1000,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if min_interval_ms < 0:
            raise ValueError("min_interval_ms must be >= 0")
        self._min_interval_ms = min_interval_ms
        self._clock = clock
        self._sleeper = sleeper
        self._last_request_time: float | None = None
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if needed to respect rate limit. Call before each HTTP request."""
        async with self._lock:
            now = self._clock()
            if self._last_request_time is not None:
                elapsed_ms = (now - self._last_request_time) * 1000
                wait_ms = self._min_interval_ms - elapsed_ms
                if wait_ms > 0:
                    await self._sleeper(wait_ms / 1000)
            self._last_request_time = self._clock()
