import asyncio

from uscryptoarb.http.rate_limiter import RateLimiter


def test_first_acquire_does_not_wait() -> None:
    calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        calls.append(delay)

    limiter = RateLimiter(min_interval_ms=1000, sleeper=fake_sleep)
    asyncio.run(limiter.acquire())
    assert calls == []


def test_rapid_acquire_waits() -> None:
    timeline = iter([0.0, 0.0, 0.1, 0.1])
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    limiter = RateLimiter(min_interval_ms=1000, clock=lambda: next(timeline), sleeper=fake_sleep)

    async def run() -> None:
        await limiter.acquire()
        await limiter.acquire()

    asyncio.run(run())
    assert sleeps == [0.9]


def test_acquire_after_interval_does_not_wait() -> None:
    timeline = iter([0.0, 0.0, 1.0, 1.0])
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    limiter = RateLimiter(min_interval_ms=100, clock=lambda: next(timeline), sleeper=fake_sleep)

    async def run() -> None:
        await limiter.acquire()
        await limiter.acquire()

    asyncio.run(run())
    assert sleeps == []


def test_concurrent_acquire_serializes() -> None:
    timeline = iter([0.0, 0.0, 0.0, 0.0])
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    limiter = RateLimiter(min_interval_ms=500, clock=lambda: next(timeline), sleeper=fake_sleep)

    async def run() -> None:
        await asyncio.gather(limiter.acquire(), limiter.acquire())

    asyncio.run(run())
    assert sleeps == [0.5]


def test_custom_interval() -> None:
    timeline = iter([0.0, 0.0, 0.1, 0.1])
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    limiter = RateLimiter(min_interval_ms=250, clock=lambda: next(timeline), sleeper=fake_sleep)

    async def run() -> None:
        await limiter.acquire()
        await limiter.acquire()

    asyncio.run(run())
    assert sleeps == [0.15]
