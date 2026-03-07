"""CEX.IO async exchange connector.

Uses /api/order_book/{sym1}/{sym2} endpoint (tickers lack bid/ask sizes
per LL-060). Per-pair requests with configurable rate limiting. Inherits
retry/backoff from BaseAsyncConnector (DEC-018).

Order book format: arrays-of-arrays (LL-070), requires index-based parsing.
Timestamps: integer milliseconds via timestamp_ms field (LL-078).

Rate limit: 300 req/10 min for public API. Recommended rate_limit_ms: 2000.
Uses depth=1 query param to minimize payload (LL-079).

Error handling:
- Invalid pair: HTTP 200 with JSON ``{"error": "Invalid Symbols Pair"}`` (LL-077)
- Wrong endpoint: HTTP 404 with HTML body
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from uscryptoarb.connectors.cexio.parser import parse_cexio_book
from uscryptoarb.connectors.cexio.symbols import CEXIO_SYMBOLS
from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class CexioClient(BaseAsyncConnector):
    """Async CEX.IO public API client."""

    VENUE_NAME: ClassVar[str] = "cexio"
    DEFAULT_SYMBOLS: ClassVar[SymbolTranslator] = CEXIO_SYMBOLS

    BASE_URL: str = "https://cex.io/api"
    BOOK_PATH_PREFIX: str = "/order_book"

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
        return await self._fetch_tickers_per_pair(
            pairs,
            fetch_one=self._fetch_book,
            parse_one=parse_cexio_book,
        )

    async def _fetch_book(self, symbol: str) -> dict[str, Any]:
        """Fetch order book for a single symbol with retry.

        Uses shared _fetch_with_retry() for rate limiting and transient error
        handling, then applies CEX.IO-specific response validation.

        CEX.IO error responses:
        - Invalid pair: HTTP 200 with JSON ``{"error": "Invalid Symbols Pair"}`` (LL-077)
        - Wrong endpoint: HTTP 404 with HTML body
        """
        # CEX.IO symbols use "/" — split to build URL path segments.
        # e.g., "BTC/USD" → /order_book/BTC/USD
        url = f"{self.BASE_URL}{self.BOOK_PATH_PREFIX}/{symbol}"

        response = await self._fetch_with_retry(
            "GET",
            url,
            params={"depth": "1"},
        )

        # CEX.IO returns HTML on 404 errors.
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise ValueError(f"HTML error response for {symbol} (likely invalid endpoint)")

        try:
            data = response.json()
        except Exception as exc:
            raise ValueError(f"Non-JSON response for {symbol}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object for {symbol}, got {type(data).__name__}")

        # CEX.IO JSON error envelope: {"error": "Invalid Symbols Pair"} (LL-077)
        if "error" in data:
            raise ValueError(f"CEX.IO API error for {symbol}: {data['error']}")

        return data
