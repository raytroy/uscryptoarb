from __future__ import annotations

import logging
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_nonempty_list

logger = logging.getLogger(__name__)


def parse_book_response(
    raw: dict[str, Any],
    canonical_pair: str,
    ts_local_ms: int,
) -> TopOfBook:
    """Parse a Gemini /v1/book response into a TopOfBook.

    Gemini book responses have top-level bids/asks arrays (no wrapper like
    Coinbase's "pricebook"). Each element is
    {"price": str, "amount": str, "timestamp": str}. Timestamps are Unix
    seconds as integer strings (LL-063).

    Args:
        raw: Raw JSON response from /v1/book/{symbol}?limit_bids=1&limit_asks=1
        canonical_pair: Canonical pair (e.g., "BTC/USD")
        ts_local_ms: Local timestamp when data was received (ms since epoch)

    Returns:
        TopOfBook instance (validated via tob_from_raw)

    Raises:
        ValueError: If bids/asks are missing, wrong type, or empty
    """
    bids_list = require_nonempty_list(raw.get("bids"), f"{canonical_pair}.bids")
    asks_list = require_nonempty_list(raw.get("asks"), f"{canonical_pair}.asks")

    best_bid = bids_list[0]
    best_ask = asks_list[0]

    # Gemini timestamps: Unix seconds as integer strings (LL-063).
    # Use the more recent of bid/ask timestamps.
    ts_exchange_ms: int | None = None
    try:
        ts_bid = int(best_bid["timestamp"])
        ts_ask = int(best_ask["timestamp"])
        ts_exchange_ms = max(ts_bid, ts_ask) * 1000
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse Gemini timestamp for %s: %s", canonical_pair, exc)

    return tob_from_raw(
        venue="gemini",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=best_bid["price"],
        bid_sz=best_bid["amount"],
        ask_px=best_ask["price"],
        ask_sz=best_ask["amount"],
    )
