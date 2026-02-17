from __future__ import annotations

import logging
from typing import Any, ClassVar

from uscryptoarb.connectors.bitstamp.parser import parse_book_response
from uscryptoarb.connectors.bitstamp.symbols import BITSTAMP_SYMBOLS
from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class BitstampClient(BaseAsyncConnector):
    VENUE_NAME: ClassVar[str] = "bitstamp"
    DEFAULT_SYMBOLS: ClassVar[SymbolTranslator] = BITSTAMP_SYMBOLS

    """Async Bitstamp public API client.

    Uses /api/v2/order_book/{symbol}/ endpoint (tickers lack bid/ask sizes
    per LL-060). Per-pair requests with configurable rate limiting. Inherits
    retry/backoff from BaseAsyncConnector (DEC-018).

    Order book format: arrays-of-arrays (LL-070), requires index-based parsing.
    Timestamps: microsecond precision via microtimestamp field (LL-071).
    """

    BASE_URL: str = "https://www.bitstamp.net"
    BOOK_PATH_PREFIX: str = "/api/v2/order_book"

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
        return await self._fetch_tickers_per_pair(
            pairs,
            fetch_one=self._fetch_book,
            parse_one=parse_book_response,
        )

    async def _fetch_book(self, symbol: str) -> dict[str, Any]:
        """Fetch order book for a single symbol with retry.

        Uses shared _fetch_with_retry() for rate limiting and transient error
        handling, then applies Bitstamp-specific response validation.

        Bitstamp error responses:
        - Invalid symbol on order book: HTTP 404 with HTML body (nginx)
        - Wrong endpoint: HTTP 404 with JSON {"message": "Not found."}
        """
        # Trailing slash required — without it some endpoints redirect (adds latency).
        url = f"{self.BASE_URL}{self.BOOK_PATH_PREFIX}/{symbol}/"

        response = await self._fetch_with_retry("GET", url)

        # Bitstamp returns HTML on some errors (404 for invalid symbols).
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise ValueError(f"HTML error response for {symbol} (likely invalid symbol)")

        try:
            data = response.json()
        except Exception as exc:
            raise ValueError(f"Non-JSON response for {symbol}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object for {symbol}, got {type(data).__name__}")

        # JSON error envelope: {"message": "Not found."} (no bids/asks keys)
        if "message" in data and "bids" not in data:
            raise ValueError(f"API error for {symbol}: {data.get('message')}")

        return data
