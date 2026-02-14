from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from uscryptoarb.connectors.kraken.parser import parse_ticker_response
from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOLS
from uscryptoarb.http.backoff import (
    DEFAULT_BACKOFF_POLICY,
    BackoffPolicy,
    compute_delay_ms,
)
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)


class KrakenClient:
    """Async Kraken public API client."""

    BASE_URL: str = "https://api.kraken.com"
    TICKER_PATH: str = "/0/public/Ticker"
    ORDERBOOK_PATH: str = "/0/public/Depth"
    ASSET_PAIRS_PATH: str = "/0/public/AssetPairs"

    def __init__(
        self,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        symbols: SymbolTranslator | None = None,
        timeout_s: float = 10.0,
        max_retries: int = 3,
        backoff: BackoffPolicy | None = None,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._symbols = symbols or KRAKEN_SYMBOLS
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff or DEFAULT_BACKOFF_POLICY

    @property
    def venue(self) -> str:
        return "kraken"

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        if not pairs:
            return {}

        symbols: list[str] = []
        for pair in pairs:
            try:
                symbols.append(self._symbols.to_venue_symbol(pair))
            except KeyError:
                logger.warning("Skipping unsupported canonical pair for Kraken: %s", pair)

        if not symbols:
            return {}

        symbol_str = ",".join(symbols)
        ts_local_ms = int(time.time() * 1000)
        result = await self._request("GET", self.TICKER_PATH, params={"pair": symbol_str})
        return parse_ticker_response(result, ts_local_ms=ts_local_ms, symbols=self._symbols)

    async def validate_symbols(self) -> None:
        result = await self._request("GET", self.ASSET_PAIRS_PATH)
        missing: list[str] = []
        for canonical, kraken_symbol in self._symbols.canonical_to_venue.items():
            if kraken_symbol not in result:
                missing.append(f"{canonical} ({kraken_symbol})")
            else:
                logger.info("Validated Kraken symbol: %s -> %s", canonical, kraken_symbol)

        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing Kraken symbol(s) from AssetPairs: {joined}")

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.BASE_URL}{path}"

        for attempt in range(self._max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    timeout=self._timeout_s,
                )
                if response.status_code >= 400:
                    response.raise_for_status()

                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Kraken response must be a JSON object")
                errors = data.get("error", [])
                if errors:
                    raise ValueError(f"Kraken API error(s): {errors}")
                result = data.get("result")
                if not isinstance(result, dict):
                    raise ValueError("Kraken result must be a JSON object")
                return result
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
                retryable = isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
                    retryable = True
                if not retryable or attempt >= self._max_retries:
                    raise

                delay_ms = compute_delay_ms(attempt, self._backoff)
                await asyncio.sleep(delay_ms / 1000)

        raise RuntimeError("unreachable")
