import asyncio
import importlib.util
from collections import deque
from collections.abc import Callable
from typing import Any

import pytest

if importlib.util.find_spec("httpx") is None:
    pytest.skip("httpx is not installed", allow_module_level=True)

import httpx

from tests.helpers import DummyRateLimiter
from uscryptoarb.connectors.gemini.client import GeminiClient
from uscryptoarb.connectors.gemini.symbols import GEMINI_SYMBOL_MAP
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter

SAMPLE_BOOK: dict[str, Any] = {
    "bids": [{"price": "68284.0", "amount": "3.0", "timestamp": "1771211101"}],
    "asks": [{"price": "68292.92", "amount": "0.01538526", "timestamp": "1771211101"}],
}

GEMINI_ERROR_RESPONSE: dict[str, Any] = {
    "result": "error",
    "reason": "Bad Request",
    "message": "Supplied value 'INVALIDPAIR' is not a valid symbol",
}

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)


def make_client(
    handler: Callable[[httpx.Request], httpx.Response | Any],
) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def make_book(symbol: str) -> dict[str, Any]:
    """Build a valid Gemini book response for any symbol."""
    if "btc" in symbol and symbol not in ("ltcbtc", "solbtc"):
        bid, ask = "68284.0", "68292.92"
    elif symbol in ("ltcbtc", "solbtc"):
        bid, ask = "0.0007979", "0.0007988"
    else:
        bid, ask = "54.50", "54.53"
    return {
        "bids": [{"price": bid, "amount": "1.0", "timestamp": "1771211101"}],
        "asks": [{"price": ask, "amount": "1.0", "timestamp": "1771211101"}],
    }


def test_fetch_tickers_happy_path() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        # Extract symbol from URL path: /v1/book/{symbol}
        symbol = str(request.url.path).rsplit("/", 1)[-1]
        return httpx.Response(200, json=make_book(symbol))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=limiter)
            out = await gc.fetch_tickers(list(GEMINI_SYMBOL_MAP))
            assert len(out) == 8

    asyncio.run(run())
    assert limiter.calls == 8


def test_fetch_tickers_filters_unknown_pairs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            out = await gc.fetch_tickers(["ETH/USD"])
            assert out == {}

    asyncio.run(run())


def test_fetch_tickers_empty_pairs_returns_empty() -> None:
    request_count = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        request_count["n"] += 1
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            assert await gc.fetch_tickers([]) == {}

    asyncio.run(run())
    assert request_count["n"] == 0


def test_fetch_tickers_partial_failure() -> None:
    call_count = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        symbol = str(request.url.path).rsplit("/", 1)[-1]
        if symbol == "solusd":
            return httpx.Response(400, json=GEMINI_ERROR_RESPONSE)
        return httpx.Response(200, json=make_book(symbol))

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0), max_retries=0)
            out = await gc.fetch_tickers(["BTC/USD", "SOL/USD", "LTC/BTC"])
            assert "BTC/USD" in out
            assert "LTC/BTC" in out
            assert "SOL/USD" not in out

    asyncio.run(run())


def test_fetch_tickers_all_fail_returns_empty() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=GEMINI_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0), max_retries=0)
            out = await gc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())


def test_gemini_error_json_in_response() -> None:
    """Gemini error envelope with HTTP 200 should be caught and logged."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=GEMINI_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            out = await gc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())


def test_gemini_non_json_error() -> None:
    """Gemini plain-text error (some 400s) should be handled gracefully."""

    async def handler(request: httpx.Request) -> httpx.Response:
        # Simulate the 200 + non-JSON edge case (shouldn't happen in practice,
        # but _fetch_book must not crash on malformed responses)
        return httpx.Response(
            200,
            text="Unexpected plain text",
            headers={"content-type": "text/plain"},
        )

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            out = await gc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())


def test_fetch_tickers_timeout_retries() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(
                client=client,
                rate_limiter=RateLimiter(0),
                backoff=FAST_BACKOFF,
            )
            out = await gc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_http_500_retries() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(
                client=client,
                rate_limiter=RateLimiter(0),
                backoff=FAST_BACKOFF,
            )
            out = await gc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_http_400_not_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json=GEMINI_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0), max_retries=3)
            out = await gc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())
    assert calls["n"] == 1


def test_rate_limiter_called_per_pair() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        symbol = str(request.url.path).rsplit("/", 1)[-1]
        return httpx.Response(200, json=make_book(symbol))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=limiter)
            await gc.fetch_tickers(["BTC/USD", "SOL/USD", "LTC/BTC"])

    asyncio.run(run())
    assert limiter.calls == 3


def test_request_url_contains_book_path() -> None:
    seen: deque[str] = deque()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            await gc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert "/v1/book/btcusd" in seen[0]


def test_request_includes_limit_params() -> None:
    seen: deque[str] = deque()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            await gc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert "limit_bids=1" in seen[0]
    assert "limit_asks=1" in seen[0]


def test_venue_property() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            gc = GeminiClient(client=client, rate_limiter=RateLimiter(0))
            assert gc.venue == "gemini"

    asyncio.run(run())
