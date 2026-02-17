from __future__ import annotations

import logging
from typing import Any, ClassVar

# Re-export for type checking — httpx is used by callers constructing clients
from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.connectors.gemini.parser import parse_book_response
from uscryptoarb.connectors.gemini.symbols import GEMINI_SYMBOLS
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class GeminiClient(BaseAsyncConnector):
    VENUE_NAME: ClassVar[str] = "gemini"
    DEFAULT_SYMBOLS: ClassVar[SymbolTranslator] = GEMINI_SYMBOLS

    """Async Gemini public API client.

    Uses /v1/book/{symbol} endpoint (not ticker — LL-062: tickers lack sizes).
    Per-pair requests with configurable rate limiting. Inherits retry/backoff
    from BaseAsyncConnector (DEC-018).
    """

    BASE_URL: str = "https://api.gemini.com"
    BOOK_PATH_PREFIX: str = "/v1/book"

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
        handling, then applies Gemini-specific response validation.

        Gemini can return non-JSON on some errors (e.g., plain text for
        invalid ticker symbols — notebook Section 8). Handles both JSON
        and plain-text error responses.
        """
        url = f"{self.BASE_URL}{self.BOOK_PATH_PREFIX}/{symbol}"
        params = {"limit_bids": "1", "limit_asks": "1"}

        response = await self._fetch_with_retry("GET", url, params=params)

        # Gemini can return non-JSON on some errors (plain text on invalid
        # ticker symbols). Try JSON first.
        try:
            data = response.json()
        except Exception as exc:
            raise ValueError(
                f"Gemini non-JSON response for {symbol}: {response.text[:200]}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(f"Gemini response for {symbol} must be a JSON object")

        # Gemini error envelope: {"result": "error", "reason": "...", "message": "..."}
        if data.get("result") == "error":
            raise ValueError(
                f"Gemini API error for {symbol}: {data.get('reason')} — {data.get('message', '')}"
            )

        return data
