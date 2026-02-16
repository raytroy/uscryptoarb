"""Tests for connectors/okx/client.py — OkxClient batch fetch logic."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from tests.helpers import DummyRateLimiter
from uscryptoarb.connectors.okx.client import OkxClient
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)


def make_okx_response(data_items: list[dict]) -> dict:
    """Wrap ticker items in OKX envelope."""
    return {"code": "0", "msg": "", "data": data_items}


def make_btc_ticker_item() -> dict:
    """Minimal valid BTC-USD ticker item."""
    return {
        "instId": "BTC-USD",
        "bidPx": "68609.3",
        "bidSz": "1.56258257",
        "askPx": "68609.4",
        "askSz": "1.46068671",
        "ts": "1771282524012",
        "instType": "SPOT",
        "last": "68622.9",
        "lastSz": "0.0001",
        "high24h": "70095",
        "low24h": "67267.9",
        "open24h": "68950.4",
        "vol24h": "199.06",
        "volCcy24h": "13618729.72",
        "sodUtc0": "68797.4",
        "sodUtc8": "67503.1",
    }


def make_sol_btc_ticker_item() -> dict:
    return {
        "instId": "SOL-BTC",
        "bidPx": "0.0012513",
        "bidSz": "50.755",
        "askPx": "0.0012516",
        "askSz": "57.8557",
        "ts": "1771282525736",
    }


def _make_client(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def test_fetch_tickers_happy_path_all_supported_pairs() -> None:
    item_map = {
        "BTC-USD": make_btc_ticker_item(),
        "BTC-USDC": {**make_btc_ticker_item(), "instId": "BTC-USDC"},
        "LTC-USD": {**make_btc_ticker_item(), "instId": "LTC-USD", "bidPx": "80", "askPx": "81"},
        "LTC-USDC": {**make_btc_ticker_item(), "instId": "LTC-USDC", "bidPx": "80", "askPx": "81"},
        "SOL-USD": {**make_btc_ticker_item(), "instId": "SOL-USD", "bidPx": "120", "askPx": "121"},
        "SOL-USDC": {
            **make_btc_ticker_item(),
            "instId": "SOL-USDC",
            "bidPx": "120",
            "askPx": "121",
        },
        "SOL-BTC": make_sol_btc_ticker_item(),
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_okx_response(list(item_map.values())))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            out = await oc.fetch_tickers(list(oc._symbols.canonical_to_venue.keys()))
            assert len(out) == 7

    asyncio.run(run())


def test_fetch_tickers_empty_pairs_returns_empty_without_api_call() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            assert await oc.fetch_tickers([]) == {}

    asyncio.run(run())
    assert calls["n"] == 0


def test_venue_property_is_okx() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            assert oc.venue == "okx"

    asyncio.run(run())


def test_single_api_call_for_multiple_pairs() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json=make_okx_response([make_btc_ticker_item(), make_sol_btc_ticker_item()]),
        )

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            await oc.fetch_tickers(["BTC/USD", "SOL/BTC"])

    asyncio.run(run())
    assert calls["n"] == 1


def test_request_includes_insttype_spot_param() -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            await oc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert "instType=SPOT" in seen_urls[0]


def test_request_url_contains_tickers_path() -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            await oc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert "/api/v5/market/tickers" in seen_urls[0]


def test_client_side_filtering_returns_only_requested_pairs() -> None:
    items = [make_btc_ticker_item(), make_sol_btc_ticker_item()]
    items.extend({**make_btc_ticker_item(), "instId": f"EXTRA-{idx}"} for idx in range(7))

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=make_okx_response(items))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            out = await oc.fetch_tickers(["BTC/USD"])
            assert set(out.keys()) == {"BTC/USD"}

    asyncio.run(run())


def test_nonzero_code_raises_value_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": "51001", "msg": "bad", "data": []})

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            with pytest.raises(ValueError, match="OKX API error"):
                await oc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())


def test_http_500_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="server error")
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(
                client=client,
                rate_limiter=RateLimiter(0),
                max_retries=1,
                backoff=FAST_BACKOFF,
            )
            out = await oc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_http_400_not_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad request")

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(
                client=client,
                rate_limiter=RateLimiter(0),
                max_retries=3,
                backoff=FAST_BACKOFF,
            )
            with pytest.raises(httpx.HTTPStatusError):
                await oc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
    assert calls["n"] == 1


def test_timeout_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json=make_okx_response([make_btc_ticker_item()]))

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            out = await oc.fetch_tickers(["BTC/USD"])
            assert "BTC/USD" in out

    asyncio.run(run())
    assert calls["n"] == 2


def test_rate_limiter_called_once_for_batch() -> None:
    limiter = DummyRateLimiter()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=make_okx_response([make_btc_ticker_item(), make_sol_btc_ticker_item()]),
        )

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=limiter, backoff=FAST_BACKOFF)
            await oc.fetch_tickers(["BTC/USD", "SOL/BTC"])

    asyncio.run(run())
    assert limiter.calls == 1


def test_non_json_response_raises() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json", headers={"content-type": "text/plain"})

    async def run() -> None:
        async with _make_client(handler) as client:
            oc = OkxClient(client=client, rate_limiter=RateLimiter(0), backoff=FAST_BACKOFF)
            with pytest.raises(ValueError):
                await oc.fetch_tickers(["BTC/USD"])

    asyncio.run(run())
