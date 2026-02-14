import asyncio
import importlib.util
from collections import deque
from collections.abc import Callable
from typing import Any

import pytest

if importlib.util.find_spec("httpx") is None:
    pytest.skip("httpx is not installed", allow_module_level=True)

import httpx

from uscryptoarb.connectors.coinbase.client import CoinbaseClient
from uscryptoarb.connectors.coinbase.symbols import COINBASE_SYMBOL_MAP
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter

SAMPLE_PRODUCT_BOOK = {
    "pricebook": {
        "product_id": "BTC-USD",
        "bids": [{"price": "69845.94", "size": "0.08400565"}],
        "asks": [{"price": "69845.95", "size": "0.10558907"}],
        "time": "2026-02-14T17:23:44.194522Z",
    },
    "last": "69845.945",
    "mid_market": "69845.945",
    "spread_bps": "0.00143172224",
    "spread_absolute": "0.01",
}

COINBASE_ERROR_RESPONSE = {
    "error": "NOT_FOUND",
    "error_details": "valid product_id is required",
    "message": "valid product_id is required",
}


class DummyRateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


def make_client(
    handler: Callable[[httpx.Request], httpx.Response | Any],
) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def make_product_book(product_id: str) -> dict[str, Any]:
    _base, quote = product_id.split("-")
    if quote == "BTC":
        bid, ask = "0.000811", "0.000812"
    else:
        bid, ask = "69845.94", "69845.95"
    return {
        "pricebook": {
            "product_id": product_id,
            "bids": [{"price": bid, "size": "1.00000000"}],
            "asks": [{"price": ask, "size": "1.00000000"}],
            "time": "2026-02-14T17:23:44.194522Z",
        },
    }


def test_fetch_tickers_happy_path() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        product_id = request.url.params.get("product_id", "")
        return httpx.Response(200, json=make_product_book(product_id))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=limiter)
            out = await cc.fetch_tickers(list(COINBASE_SYMBOL_MAP))
            assert len(out) == 8

    asyncio.run(run())
    assert limiter.calls == 8


def test_fetch_tickers_filters_unknown_pairs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0))
            out = await cc.fetch_tickers(["ETH/USD"])
            assert out == {}

    asyncio.run(run())


def test_fetch_tickers_empty_pairs_returns_empty() -> None:
    request_count = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        request_count["n"] += 1
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0))
            assert await cc.fetch_tickers([]) == {}

    asyncio.run(run())
    assert request_count["n"] == 0


def test_fetch_tickers_partial_failure() -> None:
    call_count = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        product_id = request.url.params.get("product_id", "")
        if product_id == "SOL-USD":
            return httpx.Response(404, json=COINBASE_ERROR_RESPONSE)
        return httpx.Response(200, json=make_product_book(product_id))

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0), max_retries=0)
            out = await cc.fetch_tickers(["BTC/USD", "SOL/USD", "LTC/BTC"])
            assert "BTC/USD" in out
            assert "LTC/BTC" in out
            assert "SOL/USD" not in out

    asyncio.run(run())


def test_fetch_tickers_all_fail_returns_empty() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=COINBASE_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0), max_retries=0)
            out = await cc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())


def test_coinbase_error_json_in_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=COINBASE_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0), max_retries=0)
            out = await cc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())


def test_fetch_tickers_timeout_retries() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(
                client=client,
                rate_limiter=RateLimiter(0),
                backoff=BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0),
            )
            out = await cc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_http_500_retries() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(
                client=client,
                rate_limiter=RateLimiter(0),
                backoff=BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0),
            )
            out = await cc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_http_404_not_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json=COINBASE_ERROR_RESPONSE)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0), max_retries=3)
            out = await cc.fetch_tickers(["BTC/USD"])
            assert out == {}

    asyncio.run(run())
    assert calls["n"] == 1


def test_rate_limiter_called_per_pair() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        product_id = request.url.params.get("product_id", "")
        return httpx.Response(200, json=make_product_book(product_id))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=limiter)
            await cc.fetch_tickers(["BTC/USD", "SOL/USD", "LTC/BTC"])

    asyncio.run(run())
    assert limiter.calls == 3


def test_request_includes_product_id_param() -> None:
    seen: deque[str] = deque()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0))
            await cc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert "product_id=BTC-USD" in seen[0]
    assert "limit=1" in seen[0]


def test_cache_control_header_present() -> None:
    seen_headers: deque[dict[str, str]] = deque()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0))
            await cc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert seen_headers[0].get("cache-control") == "no-cache"


def test_venue_property() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_PRODUCT_BOOK)

    async def run() -> None:
        async with make_client(handler) as client:
            cc = CoinbaseClient(client=client, rate_limiter=RateLimiter(0))
            assert cc.venue == "coinbase"

    asyncio.run(run())
