"""CEX.IO order book response parser.

CEX.IO order book entries are arrays-of-arrays (LL-070 pattern):
    bids: [[price, amount], ...]   # floats (not strings)
    asks: [[price, amount], ...]
Index-based access: [0] = price, [1] = amount.

Timestamps: ``timestamp_ms`` field provides Unix milliseconds as an
integer (LL-078 — simplest format, no conversion needed). Fallback to
``timestamp`` (Unix seconds as integer) × 1000.

CEX.IO returns HTTP 200 for invalid pairs with ``{"error": "..."}``
(LL-077). That case is handled in the client, not the parser.
"""

from __future__ import annotations

import logging
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_nonempty_list

logger = logging.getLogger(__name__)


def parse_cexio_book(
    raw: dict[str, Any],
    canonical_pair: str,
    ts_local_ms: int,
) -> TopOfBook:
    """Parse a CEX.IO /api/order_book/{sym1}/{sym2} response into a TopOfBook.

    Args:
        raw: Raw JSON response from CEX.IO order book endpoint.
        canonical_pair: Canonical pair (e.g., "BTC/USD").
        ts_local_ms: Local timestamp when data was received (ms since epoch).

    Returns:
        TopOfBook instance (validated via tob_from_raw).

    Raises:
        ValueError: If bids/asks are missing, wrong type, or empty.
    """
    bids_list = require_nonempty_list(raw.get("bids"), f"{canonical_pair}.bids")
    asks_list = require_nonempty_list(raw.get("asks"), f"{canonical_pair}.asks")

    best_bid = bids_list[0]  # [price, amount]
    best_ask = asks_list[0]  # [price, amount]

    # CEX.IO timestamp_ms is an integer (LL-078). Fall back to timestamp * 1000.
    ts_exchange_ms: int | None = None
    try:
        if "timestamp_ms" in raw:
            ts_exchange_ms = int(raw["timestamp_ms"])
        elif "timestamp" in raw:
            ts_exchange_ms = int(raw["timestamp"]) * 1000
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse CEX.IO timestamp for %s: %s", canonical_pair, exc)

    return tob_from_raw(
        venue="cexio",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=str(best_bid[0]),  # Index 0 = price (LL-070)
        bid_sz=str(best_bid[1]),  # Index 1 = amount
        ask_px=str(best_ask[0]),
        ask_sz=str(best_ask[1]),
    )
