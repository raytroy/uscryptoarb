"""Crypto.com async exchange connector.

Uses /public/get-book endpoint (tickers lack bid/ask sizes per LL-080).
Per-pair requests with configurable rate limiting. Inherits retry/backoff
from BaseAsyncConnector (DEC-018).

Order book format: arrays-of-arrays with strings (LL-070 pattern):
    bids: [["price", "size", "num_orders"], ...]
Timestamps: Unix milliseconds as integer in ``t`` field.

Response envelope: ``{"code": 0, "result": {"data": [...]}}``.
Code 0 = success (integer, not string like OKX — LL-081).

Error handling:
- Invalid instrument: HTTP 200 with ``code != 0`` and error message
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.connectors.cryptodotcom.parser import parse_cryptodotcom_book
from uscryptoarb.connectors.cryptodotcom.symbols import CRYPTODOTCOM_SYMBOLS
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class CryptodotcomClient(BaseAsyncConnector):
    """Async Crypto.com Exchange public API client."""

    VENUE_NAME: ClassVar[str] = "cryptodotcom"
    DEFAULT_SYMBOLS: ClassVar[SymbolTranslator] = CRYPTODOTCOM_SYMBOLS

    BASE_URL: str = "https://api.crypto.com/exchange/v1"
    BOOK_PATH: str = "/public/get-book"

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
        return await self._fetch_tickers_per_pair(
            pairs,
            fetch_one=self._fetch_book,
            parse_one=parse_cryptodotcom_book,
        )

    async def _fetch_book(self, symbol: str) -> dict[str, Any]:
        """Fetch order book for a single symbol with retry.

        Uses shared _fetch_with_retry() for rate limiting and transient error
        handling, then applies Crypto.com-specific envelope validation.

        Returns the inner data dict (``result.data[0]``), not the full envelope.
        """
        url = f"{self.BASE_URL}{self.BOOK_PATH}"

        response = await self._fetch_with_retry(
            "GET",
            url,
            params={"instrument_name": symbol, "depth": "5"},
        )

        try:
            envelope = response.json()
        except Exception as exc:
            raise ValueError(f"Non-JSON response for {symbol}") from exc

        if not isinstance(envelope, dict):
            raise ValueError(
                f"Expected JSON object for {symbol}, got {type(envelope).__name__}"
            )

        # Crypto.com uses integer code (LL-081): 0 = success.
        code = envelope.get("code")
        if code != 0:
            msg = envelope.get("msg", envelope.get("message", ""))
            raise ValueError(f"Crypto.com API error for {symbol}: code={code} msg={msg}")

        # Extract inner data: result.data[0]
        result = envelope.get("result")
        if not isinstance(result, dict):
            raise ValueError(f"Missing 'result' in Crypto.com response for {symbol}")

        data_list = result.get("data")
        if not isinstance(data_list, list) or not data_list:
            raise ValueError(f"Missing or empty 'result.data' for {symbol}")

        book: dict[str, Any] = data_list[0]
        return book
