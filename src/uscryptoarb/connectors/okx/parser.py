"""OKX US response parsers.

parse_okx_ticker: Parses a single ticker item from the batch response.
parse_batch_tickers: Parses the full batch response envelope, validates
    code == "0" (LL-070), filters to known pairs, returns dict of TopOfBook.

OKX timestamps are Unix milliseconds as strings — just int(ts), no
multiplication by 1000 (LL-071).
"""

from __future__ import annotations

import logging
from typing import Any

from uscryptoarb.marketdata.topofbook import TopOfBook, tob_from_raw
from uscryptoarb.validation.guards import require_nonempty_list
from uscryptoarb.venues.symbol_translator import SymbolTranslator

logger = logging.getLogger(__name__)


def parse_okx_ticker(
    data: dict[str, Any],
    canonical_pair: str,
    ts_local_ms: int,
) -> TopOfBook:
    """Parse a single OKX ticker item into TopOfBook.

    Args:
        data: Single ticker dict from the data array
            (keys: instId, bidPx, bidSz, askPx, askSz, ts, ...).
        canonical_pair: Canonical pair string (e.g. "BTC/USD").
        ts_local_ms: Local timestamp when data was received (ms).

    Returns:
        TopOfBook validated via tob_from_raw (DEC-003).

    Raises:
        KeyError: If required fields are missing.
        ValueError: If tob_from_raw validation fails.
    """
    ts_exchange_ms: int | None = None
    try:
        ts_exchange_ms = int(data["ts"])
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Failed to parse OKX timestamp for %s: %s", canonical_pair, exc)

    return tob_from_raw(
        venue="okx",
        pair=canonical_pair,
        ts_local_ms=ts_local_ms,
        ts_exchange_ms=ts_exchange_ms,
        bid_px=data["bidPx"],
        bid_sz=data["bidSz"],
        ask_px=data["askPx"],
        ask_sz=data["askSz"],
    )


def parse_batch_tickers(
    raw: dict[str, Any],
    ts_local_ms: int,
    symbols: SymbolTranslator,
) -> dict[str, TopOfBook]:
    """Parse OKX batch tickers response into dict of TopOfBook.

    Validates code == "0" (LL-070), filters to known pairs,
    gracefully skips parse failures.

    Args:
        raw: Full OKX API response: {"code": "0", "msg": "", "data": [...]}.
        ts_local_ms: Local timestamp when data was received (ms).
        symbols: SymbolTranslator for venue→canonical lookup.

    Returns:
        Dict of canonical_pair → TopOfBook for successfully parsed pairs.

    Raises:
        ValueError: If code != "0" or data array is missing/empty.
    """
    code = raw.get("code", "")
    if code != "0":
        msg = raw.get("msg", "")
        raise ValueError(f"OKX API error: code={code} msg={msg}")

    data_list = require_nonempty_list(raw.get("data"), "OKX tickers data")

    results: dict[str, TopOfBook] = {}
    for item in data_list:
        inst_id = item.get("instId", "")
        try:
            canonical = symbols.to_canonical(inst_id)
        except KeyError:
            continue

        try:
            tob = parse_okx_ticker(item, canonical, ts_local_ms)
            results[canonical] = tob
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse OKX ticker for %s (%s): %s", canonical, inst_id, exc)

    return results
