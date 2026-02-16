"""Tests for connectors/base.py — BaseAsyncConnector shared retry logic.

Uses a minimal concrete subclass to test _fetch_with_retry() directly,
isolating the shared retry/backoff/rate-limit behavior from venue-specific
response parsing.
"""

import asyncio
import importlib.util

import pytest

if importlib.util.find_spec("httpx") is None:
    pytest.skip("httpx is not installed", allow_module_level=True)

import httpx

from tests.helpers import DummyRateLimiter
from uscryptoarb.connectors.base import BaseAsyncConnector
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator


# Minimal concrete subclass for testing the ABC
class StubConnector(BaseAsyncConnector):
    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        return {}


STUB_SYMBOLS = SymbolTranslator(venue="stub", canonical_to_venue={"BTC/USD": "BTC-USD"})
FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


def _make_connector(client, rate_limiter=None, max_retries=3, backoff=None):
    return StubConnector(
        client=client,
        rate_limiter=rate_limiter or RateLimiter(0),
        symbols=STUB_SYMBOLS,
        venue_name="stub",
        max_retries=max_retries,
        backoff=backoff or FAST_BACKOFF,
    )


def test_venue_property() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            assert c.venue == "stub"

    asyncio.run(run())


def test_fetch_success_first_attempt() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            resp = await c._fetch_with_retry("GET", "http://test/api")
            assert resp.status_code == 200
            assert resp.json() == {"ok": True}

    asyncio.run(run())


def test_timeout_retries_then_succeeds() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            resp = await c._fetch_with_retry("GET", "http://test/api")
            assert resp.status_code == 200

    asyncio.run(run())
    assert calls["n"] == 3


def test_connect_error_retries_then_succeeds() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            resp = await c._fetch_with_retry("GET", "http://test/api")
            assert resp.status_code == 200

    asyncio.run(run())
    assert calls["n"] == 2


def test_500_retries_then_succeeds() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            resp = await c._fetch_with_retry("GET", "http://test/api")
            assert resp.status_code == 200

    asyncio.run(run())
    assert calls["n"] == 2


def test_429_retries_then_succeeds() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            resp = await c._fetch_with_retry("GET", "http://test/api")
            assert resp.status_code == 200

    asyncio.run(run())
    assert calls["n"] == 2


def test_404_not_retried() -> None:
    calls = {"n": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, text="Not Found")

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client, max_retries=3)
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await c._fetch_with_retry("GET", "http://test/api")
            assert exc_info.value.response.status_code == 404

    asyncio.run(run())
    assert calls["n"] == 1


def test_exhausted_retries_raises_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client, max_retries=2)
            with pytest.raises(httpx.TimeoutException):
                await c._fetch_with_retry("GET", "http://test/api")

    asyncio.run(run())


def test_exhausted_retries_raises_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Unavailable")

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client, max_retries=1)
            with pytest.raises(httpx.HTTPStatusError):
                await c._fetch_with_retry("GET", "http://test/api")

    asyncio.run(run())


def test_rate_limiter_called_per_attempt() -> None:
    calls = {"n": 0}
    limiter = DummyRateLimiter()

    async def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.TimeoutException("timeout")
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client, rate_limiter=limiter)
            await c._fetch_with_retry("GET", "http://test/api")

    asyncio.run(run())
    assert limiter.calls == 2  # once per attempt


def test_headers_passed_through() -> None:
    seen_headers: list[dict[str, str]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(dict(request.headers))
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            await c._fetch_with_retry(
                "GET", "http://test/api", headers={"cache-control": "no-cache"}
            )

    asyncio.run(run())
    assert seen_headers[0].get("cache-control") == "no-cache"


def test_params_passed_through() -> None:
    seen_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"ok": True})

    async def run() -> None:
        async with _make_client(handler) as client:
            c = _make_connector(client)
            await c._fetch_with_retry("GET", "http://test/api", params={"product_id": "BTC-USD"})

    asyncio.run(run())
    assert "product_id=BTC-USD" in seen_urls[0]
