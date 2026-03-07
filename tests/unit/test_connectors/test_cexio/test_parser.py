"""Tests for CEX.IO order book parser."""

from decimal import Decimal

import pytest

from uscryptoarb.connectors.cexio.parser import parse_cexio_book

TS_LOCAL = 1772915500000


def _book(
    *,
    bid_px: float = 67233.5,
    bid_sz: float = 0.025,
    ask_px: float = 67271.0,
    ask_sz: float = 0.025,
    ts_ms: int = 1772915479528,
    ts_s: int = 1772915480,
) -> dict:
    return {
        "timestamp": ts_s,
        "timestamp_ms": ts_ms,
        "bids": [[bid_px, bid_sz]],
        "asks": [[ask_px, ask_sz]],
        "pair": "BTC:USD",
        "id": 123456,
    }


def test_happy_path_btc_usd() -> None:
    tob = parse_cexio_book(_book(), "BTC/USD", TS_LOCAL)
    assert tob.venue == "cexio"
    assert tob.pair == "BTC/USD"
    assert tob.bid_px == Decimal("67233.5")
    assert tob.ask_px == Decimal("67271.0")
    assert tob.bid_sz == Decimal("0.025")
    assert tob.ask_sz == Decimal("0.025")


def test_returns_decimal_types() -> None:
    tob = parse_cexio_book(_book(), "BTC/USD", TS_LOCAL)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_bid_less_than_ask() -> None:
    tob = parse_cexio_book(_book(), "BTC/USD", TS_LOCAL)
    assert tob.bid_px < tob.ask_px


def test_missing_bids_raises() -> None:
    raw = _book()
    del raw["bids"]
    with pytest.raises((ValueError, TypeError)):
        parse_cexio_book(raw, "BTC/USD", TS_LOCAL)


def test_missing_asks_raises() -> None:
    raw = _book()
    del raw["asks"]
    with pytest.raises((ValueError, TypeError)):
        parse_cexio_book(raw, "BTC/USD", TS_LOCAL)


def test_empty_bids_raises() -> None:
    raw = _book()
    raw["bids"] = []
    with pytest.raises(ValueError):
        parse_cexio_book(raw, "BTC/USD", TS_LOCAL)


def test_empty_asks_raises() -> None:
    raw = _book()
    raw["asks"] = []
    with pytest.raises(ValueError):
        parse_cexio_book(raw, "BTC/USD", TS_LOCAL)


def test_timestamp_ms_used_when_present() -> None:
    tob = parse_cexio_book(_book(ts_ms=1772915479528), "BTC/USD", TS_LOCAL)
    assert tob.ts_exchange_ms == 1772915479528


def test_fallback_to_timestamp_seconds() -> None:
    raw = _book()
    del raw["timestamp_ms"]
    tob = parse_cexio_book(raw, "BTC/USD", TS_LOCAL)
    # timestamp=1772915480 → 1772915480000 ms
    assert tob.ts_exchange_ms == 1772915480 * 1000


def test_no_timestamp_returns_none() -> None:
    raw = _book()
    del raw["timestamp_ms"]
    del raw["timestamp"]
    tob = parse_cexio_book(raw, "BTC/USD", TS_LOCAL)
    assert tob.ts_exchange_ms is None


def test_sol_usd_precision() -> None:
    raw = _book(bid_px=82.7157, bid_sz=2.0, ask_px=82.9742, ask_sz=2.0)
    raw["pair"] = "SOL:USD"
    tob = parse_cexio_book(raw, "SOL/USD", TS_LOCAL)
    assert tob.bid_px == Decimal("82.7157")
    assert tob.ask_px == Decimal("82.9742")
