from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from uscryptoarb.misc.decimals import DecimalLike, to_decimal


@dataclass(frozen=True, slots=True)
class TopOfBook:
    venue: str
    pair: str  # canonical BASE/QUOTE like "SOL/USDC"
    ts_local_ms: int  # local receive time in ms since epoch
    ts_exchange_ms: Optional[int]  # exchange-provided time if available

    bid_px: Decimal
    bid_sz: Decimal
    ask_px: Decimal
    ask_sz: Decimal


def validate_tob(t: TopOfBook) -> None:
    # basic presence
    if not t.venue:
        raise ValueError("venue is required")
    if not t.pair or "/" not in t.pair:
        raise ValueError("pair must be canonical like BASE/QUOTE")

    # money correctness
    for name, v in (
        ("bid_px", t.bid_px),
        ("bid_sz", t.bid_sz),
        ("ask_px", t.ask_px),
        ("ask_sz", t.ask_sz),
    ):
        if v is None:
            raise ValueError(f"{name} is required")
        if v < 0:
            raise ValueError(f"{name} must be >= 0")

    # sanity: if both sides present, enforce book ordering
    if t.bid_px > 0 and t.ask_px > 0 and t.bid_px >= t.ask_px:
        raise ValueError("crossed or locked book: bid_px must be < ask_px")


def tob_from_raw(
    *,
    venue: str,
    pair: str,
    ts_local_ms: int,
    ts_exchange_ms: Optional[int],
    bid_px: DecimalLike,
    bid_sz: DecimalLike,
    ask_px: DecimalLike,
    ask_sz: DecimalLike,
) -> TopOfBook:
    """
    Convenience constructor that converts numeric-ish inputs to Decimal via to_decimal().
    Rejects floats through to_decimal().
    """
    t = TopOfBook(
        venue=venue,
        pair=pair,
        ts_local_ms=int(ts_local_ms),
        ts_exchange_ms=None if ts_exchange_ms is None else int(ts_exchange_ms),
        bid_px=to_decimal(bid_px),
        bid_sz=to_decimal(bid_sz),
        ask_px=to_decimal(ask_px),
        ask_sz=to_decimal(ask_sz),
    )
    validate_tob(t)
    return t
