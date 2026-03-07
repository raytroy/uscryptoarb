"""Tests for CEX.IO client."""

import asyncio
from typing import Any

import httpx

from uscryptoarb.connectors.cexio.client import CexioClient
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)


def _make_client(handler) -> CexioClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return CexioClient(
        client=http_client,
        rate_limiter=RateLimiter(0),
        max_retries=1,
        backoff=FAST_BACKOFF,
    )


def _book_response(bid: str = "67233.5", ask: str = "67271.0") -> dict[str, Any]:
    return {
        "timestamp": 1772915480,
        "timestamp_ms": 1772915479528,
        "bids": [[float(bid), 0.025]],
        "asks": [[float(ask), 0.025]],
        "pair": "BTC:USD",
        "id": 123456,
    }


def test_fetch_tickers_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_book_response())

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USD"])
        assert "BTC/USD" in result
        tob = result["BTC/USD"]
        assert tob.venue == "cexio"
        assert tob.pair == "BTC/USD"

    asyncio.run(run())


def test_fetch_tickers_empty_pairs_returns_empty() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_book_response())

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers([])
        assert result == {}
        assert call_count == 0

    asyncio.run(run())


def test_fetch_tickers_json_error_skips_pair() -> None:
    """CEX.IO returns HTTP 200 with {"error": "..."} for invalid pairs (LL-077)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "Invalid Symbols Pair"})

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USDC"])
        assert result == {}

    asyncio.run(run())


def test_fetch_tickers_html_error_skips_pair() -> None:
    """CEX.IO returns HTML on 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"<html>Not Found</html>",
            headers={"content-type": "text/html"},
        )

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USD"])
        assert result == {}

    asyncio.run(run())


def test_depth_1_query_param_in_url() -> None:
    """Verify depth=1 is passed as query param (LL-079)."""
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json=_book_response())

    client = _make_client(handler)

    async def run() -> None:
        await client.fetch_tickers(["BTC/USD"])
        assert len(captured_urls) == 1
        assert "depth=1" in captured_urls[0]

    asyncio.run(run())


def test_url_construction_uses_slash_segments() -> None:
    """Verify BTC/USD becomes /order_book/BTC/USD in URL path."""
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json=_book_response())

    client = _make_client(handler)

    async def run() -> None:
        await client.fetch_tickers(["BTC/USD"])
        assert "/order_book/BTC/USD" in captured_urls[0]

    asyncio.run(run())
