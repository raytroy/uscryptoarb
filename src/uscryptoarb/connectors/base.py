from __future__ import annotations

from typing import Protocol

from uscryptoarb.marketdata.topofbook import TopOfBook


class ExchangeConnector(Protocol):
    """Protocol for exchange connectors."""

    @property
    def venue(self) -> str:
        """Venue identifier (e.g., 'kraken')."""

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""
