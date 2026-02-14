import asyncio
import importlib.util
from collections import deque

import pytest

if importlib.util.find_spec("httpx") is None:
    pytest.skip("httpx is not installed", allow_module_level=True)

import httpx

from uscryptoarb.connectors.kraken.client import KrakenClient
from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOL_MAP
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter


def make_kraken_response(result: dict, errors: list | None = None) -> dict:
    return {"error": errors or [], "result": result}


class DummyRateLimiter:
    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


def make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def test_fetch_tickers_happy_path(kraken_ticker_fixture) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response(kraken_ticker_fixture))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=limiter)
            out = await kc.fetch_tickers(list(KRAKEN_SYMBOL_MAP))
            assert len(out) == 8

    asyncio.run(run())


def test_fetch_tickers_filters_unknown_pairs(kraken_ticker_fixture) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response(kraken_ticker_fixture))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            out = await kc.fetch_tickers(["ETH/USD"])
            assert out == {}

    asyncio.run(run())


def test_fetch_tickers_api_error_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response({}, ["EGeneral:Invalid arguments"]))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            with pytest.raises(ValueError):
                await kc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())


def test_fetch_tickers_http_error_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": [], "result": {}})

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(
                client=client,
                rate_limiter=RateLimiter(0),
                max_retries=1,
                backoff=BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0),
            )
            with pytest.raises(httpx.HTTPStatusError):
                await kc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())


def test_fetch_tickers_timeout_retries(kraken_ticker_fixture) -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json=make_kraken_response(kraken_ticker_fixture))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(
                client=client,
                rate_limiter=RateLimiter(0),
                backoff=BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0),
            )
            out = await kc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_validate_symbols_happy_path(kraken_asset_pairs_fixture) -> None:
    symbols = dict(KRAKEN_SYMBOL_MAP)
    payload = dict(kraken_asset_pairs_fixture)
    for symbol in symbols.values():
        payload.setdefault(symbol, {"status": "online"})

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response(payload))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            await kc.validate_symbols()

    asyncio.run(run())


def test_validate_symbols_missing_pair_raises(kraken_asset_pairs_fixture) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response(kraken_asset_pairs_fixture))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            with pytest.raises(ValueError):
                await kc.validate_symbols()

    asyncio.run(run())


def test_request_respects_rate_limit(kraken_ticker_fixture) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response(kraken_ticker_fixture))

    limiter = DummyRateLimiter()

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=limiter)
            await kc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert limiter.calls == 1


def test_request_includes_pair_param(kraken_ticker_fixture) -> None:
    seen = deque()

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=make_kraken_response(kraken_ticker_fixture))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            await kc.fetch_tickers(["BTC/USD", "SOL/USD"])

    asyncio.run(run())
    assert "pair=XXBTZUSD%2CSOLUSD" in seen[0]


def test_fetch_tickers_empty_pairs_returns_empty() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_kraken_response({}))

    async def run() -> None:
        async with make_client(handler) as client:
            kc = KrakenClient(client=client, rate_limiter=RateLimiter(0))
            assert await kc.fetch_tickers([]) == {}

    asyncio.run(run())
