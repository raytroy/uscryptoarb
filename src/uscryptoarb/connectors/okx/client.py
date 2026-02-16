"""OKX US async exchange client.

Batch ticker pattern (like Kraken): single API call to
GET /api/v5/market/tickers?instType=SPOT returns all spot tickers.
Client-side filtering to our 7 target pairs.

Uses BaseAsyncConnector (DEC-018) for shared retry/backoff/rate-limit.
OKX-specific envelope validation (code == "0") in parse_batch_tickers (LL-070).
"""

from __future__ import annotations

from typing import Any

import httpx

from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.connectors.okx.parser import parse_batch_tickers
from uscryptoarb.connectors.okx.symbols import OKX_SYMBOLS
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.misc.time_utils import now_ms
from uscryptoarb.venues.symbol_translator import SymbolTranslator


class OkxClient(BaseAsyncConnector):
    """Async OKX US public API client.

    Uses batch ticker endpoint for all pairs in a single request.
    Inherits retry/backoff from BaseAsyncConnector (DEC-018).
    """

    BASE_URL: str = "https://app.okx.com"
    TICKERS_PATH: str = "/api/v5/market/tickers"

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
            symbols=symbols or OKX_SYMBOLS,
            venue_name="okx",
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff=backoff,
        )

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs via batch endpoint.

        Single API call fetches all SPOT tickers.
        Client-side filtering to requested pairs.
        """
        if not pairs:
            return {}

        raw = await self._request("GET", self.TICKERS_PATH, params={"instType": "SPOT"})
        ts_local_ms = now_ms()
        all_tobs = parse_batch_tickers(raw, ts_local_ms=ts_local_ms, symbols=self._symbols)

        return {pair: tob for pair, tob in all_tobs.items() if pair in pairs}

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """OKX API request: shared retry + basic JSON validation."""
        url = f"{self.BASE_URL}{path}"
        response = await self._fetch_with_retry(method, url, params=params)

        data: Any = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"OKX response must be a JSON object, got {type(data).__name__}")

        return data
