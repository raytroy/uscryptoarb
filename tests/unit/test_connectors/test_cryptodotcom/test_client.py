"""Tests for Crypto.com client."""

import asyncio
from typing import Any

import httpx

from uscryptoarb.connectors.cryptodotcom.client import CryptodotcomClient
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)


def _make_client(handler) -> CryptodotcomClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return CryptodotcomClient(
        client=http_client,
        rate_limiter=RateLimiter(0),
        max_retries=1,
        backoff=FAST_BACKOFF,
    )


def _book_envelope(bid: str = "67276.63", ask: str = "67276.64") -> dict[str, Any]:
    """Full Crypto.com response envelope."""
    return {
        "id": 1,
        "method": "public/get-book",
        "code": 0,
        "result": {
            "data": [
                {
                    "bids": [[bid, "1.0", "1"]],
                    "asks": [[ask, "1.0", "1"]],
                    "t": 1772915676741,
                }
            ],
            "instrument_name": "BTC_USD",
        },
    }


def test_fetch_tickers_happy_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_book_envelope())

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USD"])
        assert "BTC/USD" in result
        tob = result["BTC/USD"]
        assert tob.venue == "cryptodotcom"
        assert tob.pair == "BTC/USD"

    asyncio.run(run())


def test_fetch_tickers_empty_pairs_returns_empty() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_book_envelope())

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers([])
        assert result == {}
        assert call_count == 0

    asyncio.run(run())


def test_api_error_code_skips_pair() -> None:
    """Crypto.com returns code != 0 for errors (LL-081)."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": -1, "method": "public/get-book",
                "code": 10001, "msg": "Invalid instrument_name",
            },
        )

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USD"])
        assert result == {}

    asyncio.run(run())


def test_missing_result_skips_pair() -> None:
    """Missing 'result' in envelope should be handled gracefully."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 0})

    client = _make_client(handler)

    async def run() -> None:
        result = await client.fetch_tickers(["BTC/USD"])
        assert result == {}

    asyncio.run(run())


def test_instrument_name_in_query_params() -> None:
    """Verify instrument_name is passed as query param."""
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json=_book_envelope())

    client = _make_client(handler)

    async def run() -> None:
        await client.fetch_tickers(["BTC/USD"])
        assert len(captured_urls) == 1
        assert "instrument_name=BTC_USD" in captured_urls[0]

    asyncio.run(run())


def test_depth_param_in_query() -> None:
    """Verify depth=5 is passed as query param."""
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(200, json=_book_envelope())

    client = _make_client(handler)

    async def run() -> None:
        await client.fetch_tickers(["BTC/USD"])
        assert "depth=5" in captured_urls[0]

    asyncio.run(run())
