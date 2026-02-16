"""Exchange connector interfaces.

ExchangeConnector: Protocol (structural typing) for any connector.
BaseAsyncConnector: ABC with shared constructor, venue property,
    and HTTP retry-with-backoff logic. Subclasses implement
    fetch_tickers() and venue-specific response parsing.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Protocol

import httpx

from uscryptoarb.http.backoff import (
    DEFAULT_BACKOFF_POLICY,
    BackoffPolicy,
    compute_delay_ms,
)
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)


class ExchangeConnector(Protocol):
    """Protocol for exchange connectors."""

    @property
    def venue(self) -> str:
        """Venue identifier (e.g., 'kraken')."""

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs."""


class BaseAsyncConnector(ABC):
    """Base class for async exchange connectors.

    Provides:
    - Shared constructor (client, rate_limiter, symbols, timeout, retries, backoff)
    - venue property
    - _fetch_with_retry() — HTTP request with rate limiting, retry on transient
      errors (timeout, connection, 5xx, 429), and exponential backoff

    Subclasses implement:
    - fetch_tickers() — venue-specific fetch and parse logic
    - Any additional request methods that call _fetch_with_retry()

    Design note (DEC-018): _fetch_with_retry returns a raw httpx.Response.
    Each subclass handles its own JSON parsing and error extraction, since
    response formats differ across exchanges (e.g. Kraken wraps in
    {"error": [], "result": {...}}, Coinbase returns {"pricebook": {...}}).
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        rate_limiter: RateLimiter,
        symbols: SymbolTranslator,
        venue_name: str,
        timeout_s: float = 10.0,
        max_retries: int = 3,
        backoff: BackoffPolicy | None = None,
    ) -> None:
        self._client = client
        self._rate_limiter = rate_limiter
        self._symbols = symbols
        self._venue_name = venue_name
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff or DEFAULT_BACKOFF_POLICY

    @property
    def venue(self) -> str:
        """Venue identifier."""
        return self._venue_name

    async def _fetch_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute HTTP request with rate limiting, retry, and backoff.

        Returns the raw httpx.Response on the first successful (2xx) response.
        Retries on transient errors: timeouts, connection errors, HTTP 5xx,
        and HTTP 429 (rate limit). Non-retryable HTTP errors (4xx except 429)
        raise immediately.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            params: Optional query parameters.
            headers: Optional request headers.

        Returns:
            httpx.Response with status < 400.

        Raises:
            httpx.TimeoutException: If all retries exhausted on timeout.
            httpx.ConnectError: If all retries exhausted on connection error.
            httpx.HTTPStatusError: If non-retryable HTTP error, or retries exhausted.
        """
        for attempt in range(self._max_retries + 1):
            try:
                await self._rate_limiter.acquire()
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_s,
                )
                if response.status_code >= 400:
                    response.raise_for_status()
                return response

            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt >= self._max_retries:
                    raise
                delay_ms = compute_delay_ms(attempt, self._backoff)
                logger.debug(
                    "%s transient error (attempt %d/%d). Retrying in %dms.",
                    self._venue_name,
                    attempt + 1,
                    self._max_retries + 1,
                    delay_ms,
                )
                await asyncio.sleep(delay_ms / 1000)

            except httpx.HTTPStatusError as exc:
                retryable = exc.response.status_code >= 500 or exc.response.status_code == 429
                if not retryable or attempt >= self._max_retries:
                    raise
                delay_ms = compute_delay_ms(attempt, self._backoff)
                logger.debug(
                    "%s HTTP %d (attempt %d/%d). Retrying in %dms.",
                    self._venue_name,
                    exc.response.status_code,
                    attempt + 1,
                    self._max_retries + 1,
                    delay_ms,
                )
                await asyncio.sleep(delay_ms / 1000)

        raise RuntimeError("unreachable")  # pragma: no cover

    @abstractmethod
    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        """Fetch top-of-book for multiple pairs.

        Subclasses implement venue-specific fetch logic:
        - Symbol translation
        - URL construction
        - Response parsing and validation
        - Partial failure handling
        """
