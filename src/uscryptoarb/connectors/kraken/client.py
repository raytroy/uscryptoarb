from __future__ import annotations

import logging
from typing import Any, ClassVar

from uscryptoarb.connectors.connector_base import BaseAsyncConnector
from uscryptoarb.connectors.kraken.parser import parse_ticker_response
from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOLS
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.misc.time_utils import now_ms
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


class KrakenClient(BaseAsyncConnector):
    VENUE_NAME: ClassVar[str] = "kraken"
    DEFAULT_SYMBOLS: ClassVar[SymbolTranslator] = KRAKEN_SYMBOLS

    """Async Kraken public API client."""

    BASE_URL: str = "https://api.kraken.com"
    TICKER_PATH: str = "/0/public/Ticker"
    ORDERBOOK_PATH: str = "/0/public/Depth"

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
        result = await self._request("GET", self.TICKER_PATH, params={"pair": symbol_str})
        ts_local_ms = now_ms()
        return parse_ticker_response(result, ts_local_ms=ts_local_ms, symbols=self._symbols)

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
