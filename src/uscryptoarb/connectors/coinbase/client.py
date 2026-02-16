from __future__ import annotations

import logging
from typing import Any

import httpx

from uscryptoarb.connectors.coinbase.parser import parse_product_book_response
from uscryptoarb.connectors.coinbase.symbols import COINBASE_SYMBOLS
from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class CoinbaseClient(BaseAsyncConnector):
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
        super().__init__(
            client=client,
            rate_limiter=rate_limiter,
            symbols=symbols or COINBASE_SYMBOLS,
            venue_name="coinbase",
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff=backoff,
        )

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
        return await self._fetch_tickers_per_pair(
            pairs,
            fetch_one=self._fetch_product_book,
            parse_one=parse_product_book_response,
        )

    async def _fetch_product_book(self, product_id: str) -> dict[str, Any]:
        """Fetch product book for a single product_id with retry.

        Uses shared _fetch_with_retry() for rate limiting and transient error
        handling, then applies Coinbase-specific response validation.
        """
        url = f"{self.BASE_URL}{self.PRODUCT_BOOK_PATH}"
        params = {"product_id": product_id, "limit": "1"}
        headers = {"cache-control": "no-cache"}

        response = await self._fetch_with_retry("GET", url, params=params, headers=headers)

        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Coinbase response for {product_id} must be a JSON object")

        # NOTE: Pre-existing issue — in the previous code, the HTTP 4xx branch had
        # a ValueError raised inside a try/except that caught it (dead code).
        # The raise_for_status() path in _fetch_with_retry handles HTTP errors.
        # This check handles API errors returned with HTTP 200:
        if "error" in data and "pricebook" not in data:
            raise ValueError(
                f"Coinbase API error for {product_id}: "
                f"{data.get('error')} — {data.get('message', '')}"
            )

        return data
