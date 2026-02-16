from __future__ import annotations

import logging
import time
from typing import Any

# Re-export for type checking — httpx is used by callers constructing clients
import httpx

from uscryptoarb.connectors.base import BaseAsyncConnector
from uscryptoarb.connectors.gemini.parser import parse_book_response
from uscryptoarb.connectors.gemini.symbols import GEMINI_SYMBOLS
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)


class GeminiClient(BaseAsyncConnector):
    """Async Gemini public API client.

    Uses /v1/book/{symbol} endpoint (not ticker — LL-062: tickers lack sizes).
    Per-pair requests with configurable rate limiting. Inherits retry/backoff
    from BaseAsyncConnector (DEC-018).
    """

    BASE_URL: str = "https://api.gemini.com"
    BOOK_PATH_PREFIX: str = "/v1/book"

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
            symbols=symbols or GEMINI_SYMBOLS,
            venue_name="gemini",
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff=backoff,
        )

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs.

        Makes one HTTP request per pair (no batch endpoint — like Coinbase).
        Partial failures are logged and skipped; successful results returned.
        """
        if not pairs:
            return {}

        results: dict[str, TopOfBook] = {}
        for canonical in pairs:
            try:
                venue_symbol = self._symbols.to_venue_symbol(canonical)
            except KeyError:
                logger.warning("Skipping unsupported canonical pair for Gemini: %s", canonical)
                continue

            try:
                raw = await self._fetch_book(venue_symbol)
                ts_local_ms = int(time.time() * 1000)
                tob = parse_book_response(raw, canonical, ts_local_ms)
                results[canonical] = tob
            except Exception as exc:
                logger.warning(
                    "Failed to fetch Gemini ticker for %s (%s): %s",
                    canonical,
                    venue_symbol,
                    exc,
                )
                continue

        return results

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
                f"Gemini API error for {symbol}: "
                f"{data.get('reason')} — {data.get('message', '')}"
            )

        return data
