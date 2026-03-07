"""Crypto.com order book response parser.

Crypto.com order book entries are arrays-of-arrays with string values:
    bids: [["price", "size", "num_orders"], ...]
    asks: [["price", "size", "num_orders"], ...]
Index-based access: [0] = price, [1] = size.

Timestamps: ``t`` field in the book data provides Unix milliseconds as
an integer (same pattern as OKX, LL-073).

The response envelope uses ``code: 0`` for success (integer, not string
like OKX). Envelope validation happens in the client, not the parser.

Ticker endpoint lacks bid/ask sizes (LL-080), so we use the order book.
"""

from __future__ import annotations

import logging
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_nonempty_list

logger = logging.getLogger(__name__)


def parse_cryptodotcom_book(
    raw: dict[str, Any],
    canonical_pair: str,
    ts_local_ms: int,
) -> TopOfBook:
    """Parse a Crypto.com /public/get-book response data item into a TopOfBook.

    Args:
        raw: The inner data dict from ``result.data[0]`` — contains
            ``bids``, ``asks``, and ``t`` fields.
        canonical_pair: Canonical pair (e.g., "BTC/USD").
        ts_local_ms: Local timestamp when data was received (ms since epoch).

    Returns:
        TopOfBook instance (validated via tob_from_raw).

    Raises:
        ValueError: If bids/asks are missing, wrong type, or empty.
    """
    bids_list = require_nonempty_list(raw.get("bids"), f"{canonical_pair}.bids")
    asks_list = require_nonempty_list(raw.get("asks"), f"{canonical_pair}.asks")

    top_bid = bids_list[0]  # ["price", "size", "num_orders"]
    top_ask = asks_list[0]  # ["price", "size", "num_orders"]

    # Crypto.com timestamp is Unix milliseconds (integer).
    ts_exchange_ms: int | None = None
    try:
        ts_exchange_ms = int(raw["t"])
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning(
            "Failed to parse Crypto.com timestamp for %s: %s", canonical_pair, exc
        )

    return tob_from_raw(
        venue="cryptodotcom",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=top_bid[0],  # Index 0 = price
        bid_sz=top_bid[1],  # Index 1 = size
        ask_px=top_ask[0],
        ask_sz=top_ask[1],
    )
