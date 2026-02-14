from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_present

logger = logging.getLogger(__name__)


def _parse_iso_timestamp_ms(iso_str: str) -> int:
    """Convert ISO 8601 timestamp to milliseconds since epoch.

    Handles Coinbase format: "2026-02-14T17:23:44.194522Z"
    Requires Python >= 3.11 for trailing-Z support in fromisoformat().
    """
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def parse_product_book_response(
    raw: dict[str, Any],
    canonical_pair: str,
    ts_local_ms: int,
) -> TopOfBook:
    """Parse a Coinbase product_book response into a TopOfBook."""
    pricebook_obj = require_present(raw.get("pricebook"), "pricebook")
    if not isinstance(pricebook_obj, dict):
        raise ValueError("pricebook must be an object")

    bids_obj = pricebook_obj.get("bids")
    asks_obj = pricebook_obj.get("asks")

    if bids_obj is None:
        raise ValueError("Required value 'pricebook.bids' is missing")
    if asks_obj is None:
        raise ValueError("Required value 'pricebook.asks' is missing")

    if not isinstance(bids_obj, list):
        raise ValueError("pricebook.bids must be a list")
    if not isinstance(asks_obj, list):
        raise ValueError("pricebook.asks must be a list")
    if len(bids_obj) == 0:
        raise ValueError("pricebook.bids is empty")
    if len(asks_obj) == 0:
        raise ValueError("pricebook.asks is empty")

    best_bid = bids_obj[0]
    best_ask = asks_obj[0]

    ts_exchange_ms: int | None = None
    time_str = pricebook_obj.get("time")
    if time_str:
        try:
            ts_exchange_ms = _parse_iso_timestamp_ms(time_str)
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to parse Coinbase timestamp %r: %s", time_str, exc)

    return tob_from_raw(
        venue="coinbase",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=best_bid["price"],
        bid_sz=best_bid["size"],
        ask_px=best_ask["price"],
        ask_sz=best_ask["size"],
    )
