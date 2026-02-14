from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from uscryptoarb.connectors.coinbase.parser import parse_product_book_response
from uscryptoarb.connectors.coinbase.symbols import COINBASE_SYMBOLS
from uscryptoarb.http.backoff import (
    DEFAULT_BACKOFF_POLICY,
    BackoffPolicy,
    compute_delay_ms,
)
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)


class CoinbaseClient:
    """Async Coinbase public API client."""

    BASE_URL: str = "https://api.coinbase.com"
    PRODUCT_BOOK_PATH: str = "/api/v3/brokerage/market/product_book"

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
        self._symbols = symbols or COINBASE_SYMBOLS
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff or DEFAULT_BACKOFF_POLICY

    @property
    def venue(self) -> str:
        return "coinbase"

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
        if not pairs:
            return {}

        results: dict[str, TopOfBook] = {}
        for canonical in pairs:
            try:
                venue_symbol = self._symbols.to_venue_symbol(canonical)
            except KeyError:
                logger.warning(
                    "Skipping unsupported canonical pair for Coinbase: %s",
                    canonical,
                )
                continue

            try:
                raw = await self._fetch_product_book(venue_symbol)
                ts_local_ms = int(time.time() * 1000)
                tob = parse_product_book_response(raw, canonical, ts_local_ms)
                results[canonical] = tob
            except Exception as exc:
                logger.warning(
                    "Failed to fetch Coinbase ticker for %s (%s): %s",
                    canonical,
                    venue_symbol,
                    exc,
                )
                continue

        return results

    async def _fetch_product_book(self, product_id: str) -> dict[str, Any]:
        """Fetch product book for a single product_id with retry."""
        url = f"{self.BASE_URL}{self.PRODUCT_BOOK_PATH}"
        params = {"product_id": product_id, "limit": "1"}
        headers = {"cache-control": "no-cache"}

        for attempt in range(self._max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                response = await self._client.request(
                    "GET",
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_s,
                )

                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        if "error" in error_data:
                            raise ValueError(
                                f"Coinbase API error for {product_id}: "
                                f"{error_data.get('error')} — "
                                f"{error_data.get('message', '')}"
                            )
                    except (ValueError, KeyError, TypeError):
                        pass
                    response.raise_for_status()

                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError(f"Coinbase response for {product_id} must be a JSON object")

                if "error" in data and "pricebook" not in data:
                    raise ValueError(
                        f"Coinbase API error for {product_id}: "
                        f"{data.get('error')} — {data.get('message', '')}"
                    )

                return data

            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt >= self._max_retries:
                    raise
                delay_ms = compute_delay_ms(attempt, self._backoff)
                await asyncio.sleep(delay_ms / 1000)

            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code >= 500 or (exc.response.status_code == 429)
                if not retryable or attempt >= self._max_retries:
                    raise
                delay_ms = compute_delay_ms(attempt, self._backoff)
                logger.debug(
                    "Coinbase HTTP %d for %s (attempt %d/%d). Retrying in %dms.",
                    exc.response.status_code,
                    product_id,
                    attempt + 1,
                    self._max_retries + 1,
                    delay_ms,
                )
                await asyncio.sleep(delay_ms / 1000)

        raise RuntimeError("unreachable")  # pragma: no cover
