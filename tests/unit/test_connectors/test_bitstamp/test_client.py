"""Tests for connectors/bitstamp/client.py — BitstampClient fetch logic.

Uses httpx.MockTransport to simulate HTTP responses without network.
Tests cover happy path, error handling, retry logic, and rate limiting.

Key Bitstamp-specific behaviors:
- Trailing slash in URL (/api/v2/order_book/btcusd/)
- HTML 404 for invalid symbols (not JSON)
- JSON error envelope {"message": "Not found."}
"""

import asyncio
import importlib.util

import pytest

if importlib.util.find_spec("httpx") is None:
    pytest.skip("httpx is not installed", allow_module_level=True)

import httpx

from tests.helpers import DummyRateLimiter
from uscryptoarb.connectors.bitstamp.client import BitstampClient
from uscryptoarb.http.backoff import BackoffPolicy

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)

BOOK_RESPONSE = {
    "timestamp": "1771281528",
    "microtimestamp": "1771281528771691",
    "bids": [["68665", "1.40230385"]],
    "asks": [["68666", "0.15031007"]],
}


def _make_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def _make_bitstamp(client: httpx.AsyncClient, **kwargs) -> BitstampClient:
    defaults = {
        "client": client,
        "rate_limiter": DummyRateLimiter(),
        "timeout_s": 5.0,
        "max_retries": 3,
        "backoff": FAST_BACKOFF,
    }
    defaults.update(kwargs)
    return BitstampClient(**defaults)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_fetch_tickers_single_pair() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/v2/order_book/btcusd/" in str(request.url)
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in result
            assert result["BTC/USD"].venue == "bitstamp"

    asyncio.run(run())


def test_fetch_tickers_multiple_pairs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD", "LTC/USD"])
            assert len(result) == 2

    asyncio.run(run())


def test_fetch_tickers_empty_pairs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers([])
            assert result == {}

    asyncio.run(run())


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


def test_trailing_slash_in_url() -> None:
    """Bitstamp requires trailing slash on order book endpoint."""
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            await c.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert seen_urls[0].endswith("/btcusd/")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unknown_pair_skipped() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["UNKNOWN/PAIR"])
            assert result == {}

    asyncio.run(run())


def test_html_error_handled() -> None:
    """Bitstamp returns HTML 404 for invalid symbols on order book endpoint."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            content=b"<html><body>404 Not Found</body></html>",
            headers={"content-type": "text/html"},
        )

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            # fetch_tickers catches ValueError from _fetch_book and skips
            result = await c.fetch_tickers(["BTC/USD"])
            assert result == {}

    asyncio.run(run())


def test_json_error_envelope_handled() -> None:
    """Bitstamp JSON error: {"message": "Not found."}"""

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": "Not found."})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD"])
            assert result == {}

    asyncio.run(run())


def test_non_json_response_handled() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"plain text error")

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD"])
            assert result == {}

    asyncio.run(run())


def test_partial_failure_returns_successful() -> None:
    """One pair fails, other succeeds — return partial results."""
    call_count = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(
                404,
                content=b"<html>404</html>",
                headers={"content-type": "text/html"},
            )
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD", "LTC/USD"])
            assert len(result) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# Retry behavior (inherited from BaseAsyncConnector)
# ---------------------------------------------------------------------------


def test_http_500_retries() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(500)
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            result = await c.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in result

    asyncio.run(run())
    assert calls["n"] == 3


def test_rate_limiter_called() -> None:
    limiter = DummyRateLimiter()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=BOOK_RESPONSE)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client, rate_limiter=limiter)
            await c.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert limiter.calls >= 1


def test_venue_property() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_bitstamp(client)
            assert c.venue == "bitstamp"

    asyncio.run(run())
