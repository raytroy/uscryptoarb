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
    """Parse a Bitstamp /api/v2/order_book/{symbol}/ response into a TopOfBook.

    Bitstamp order book entries are arrays-of-arrays (LL-070):
        bids: [["price_str", "amount_str"], ...]
        asks: [["price_str", "amount_str"], ...]
    Index-based access: [0] = price, [1] = amount.

    Timestamps: top-level ``microtimestamp`` field provides Unix microseconds
    as a string (LL-071). Fallback to ``timestamp`` (Unix seconds as string).

    Args:
        raw: Raw JSON response from /api/v2/order_book/{symbol}/
        canonical_pair: Canonical pair (e.g., "BTC/USD")
        ts_local_ms: Local timestamp when data was received (ms since epoch)

    Returns:
        TopOfBook instance (validated via tob_from_raw)

    Raises:
        ValueError: If bids/asks are missing, wrong type, or empty
    """
    bids_list = require_nonempty_list(raw.get("bids"), f"{canonical_pair}.bids")
    asks_list = require_nonempty_list(raw.get("asks"), f"{canonical_pair}.asks")

    best_bid = bids_list[0]  # [price_str, amount_str]
    best_ask = asks_list[0]  # [price_str, amount_str]

    # Bitstamp microtimestamp: Unix microseconds as string (LL-071).
    # Prefer microtimestamp for sub-second precision; fall back to timestamp.
    ts_exchange_ms: int | None = None
    try:
        micro_ts = raw.get("microtimestamp")
        if micro_ts:
            ts_exchange_ms = int(micro_ts) // 1000
        else:
            ts_str = raw.get("timestamp")
            if ts_str:
                ts_exchange_ms = int(ts_str) * 1000
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse Bitstamp timestamp for %s: %s", canonical_pair, exc)

    return tob_from_raw(
        venue="bitstamp",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=best_bid[0],  # Index 0 = price (LL-070)
        bid_sz=best_bid[1],  # Index 1 = amount
        ask_px=best_ask[0],
        ask_sz=best_ask[1],
    )
