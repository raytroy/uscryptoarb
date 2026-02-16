from __future__ import annotations

import logging
import time
from typing import Any

from uscryptoarb.connectors.base import BaseAsyncConnector
from uscryptoarb.connectors.kraken.parser import parse_ticker_response
from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOLS
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)

# Re-export for type checking — httpx is used by callers constructing clients
import httpx  # noqa: E402


class KrakenClient(BaseAsyncConnector):
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
        super().__init__(
            client=client,
            rate_limiter=rate_limiter,
            symbols=symbols or KRAKEN_SYMBOLS,
            venue_name="kraken",
            timeout_s=timeout_s,
            max_retries=max_retries,
            backoff=backoff,
        )

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
        """Kraken API request: shared retry + Kraken-specific response validation."""
        url = f"{self.BASE_URL}{path}"
        response = await self._fetch_with_retry(method, url, params=params)

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
