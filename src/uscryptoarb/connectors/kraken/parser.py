from __future__ import annotations

import logging
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_present
from uscryptoarb.venues.symbols import SymbolTranslator

logger = logging.getLogger(__name__)


def parse_ticker_response(
    raw_result: dict[str, Any],
    ts_local_ms: int,
    symbols: SymbolTranslator,
) -> dict[str, TopOfBook]:
    parsed: dict[str, TopOfBook] = {}
    for venue_symbol, payload in raw_result.items():
        try:
            canonical = symbols.to_canonical(venue_symbol)
            asks = require_present(payload.get("a"), f"{venue_symbol}.a")
            bids = require_present(payload.get("b"), f"{venue_symbol}.b")
            parsed[canonical] = tob_from_raw(
                venue="kraken",
                pair=canonical,
                ts_local_ms=ts_local_ms,
                ts_exchange_ms=None,
                ask_px=asks[0],
                ask_sz=asks[2],
                bid_px=bids[0],
                bid_sz=bids[2],
            )
        except Exception as exc:
            logger.warning("Skipping invalid ticker for %s: %s", venue_symbol, exc)
    return parsed


def parse_orderbook_response(
    raw_result: dict[str, Any],
    canonical_pair: str,
    kraken_symbol: str,
    ts_local_ms: int,
) -> TopOfBook:
    if kraken_symbol not in raw_result:
        raise ValueError(f"Orderbook missing symbol key: {kraken_symbol}")

    symbol_book = raw_result[kraken_symbol]
    asks = require_present(symbol_book.get("asks"), f"{kraken_symbol}.asks")
    bids = require_present(symbol_book.get("bids"), f"{kraken_symbol}.bids")

    best_ask = asks[0]
    best_bid = bids[0]

    ts_exchange_ms = int(max(float(best_ask[2]), float(best_bid[2])) * 1000)

    return tob_from_raw(
        venue="kraken",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        ask_px=best_ask[0],
        ask_sz=best_ask[1],
        bid_px=best_bid[0],
        bid_sz=best_bid[1],
    )
