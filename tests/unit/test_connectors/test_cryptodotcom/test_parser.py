"""Tests for Crypto.com order book parser."""

from decimal import Decimal

import pytest

from uscryptoarb.connectors.cryptodotcom.parser import parse_cryptodotcom_book

TS_LOCAL = 1772915700000


def _book(
    *,
    bid_px: str = "67276.63",
    bid_sz: str = "0.00002",
    ask_px: str = "67276.64",
    ask_sz: str = "0.49833",
    ts: int = 1772915676741,
) -> dict:
    return {
        "bids": [[bid_px, bid_sz, "1"]],
        "asks": [[ask_px, ask_sz, "7"]],
        "t": ts,
    }


def test_happy_path_btc_usd() -> None:
    tob = parse_cryptodotcom_book(_book(), "BTC/USD", TS_LOCAL)
    assert tob.venue == "cryptodotcom"
    assert tob.pair == "BTC/USD"
    assert tob.bid_px == Decimal("67276.63")
    assert tob.ask_px == Decimal("67276.64")
    assert tob.bid_sz == Decimal("0.00002")
    assert tob.ask_sz == Decimal("0.49833")


def test_returns_decimal_types() -> None:
    tob = parse_cryptodotcom_book(_book(), "BTC/USD", TS_LOCAL)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_bid_less_than_ask() -> None:
    tob = parse_cryptodotcom_book(_book(), "BTC/USD", TS_LOCAL)
    assert tob.bid_px < tob.ask_px


def test_missing_bids_raises() -> None:
    raw = _book()
    del raw["bids"]
    with pytest.raises((ValueError, TypeError)):
        parse_cryptodotcom_book(raw, "BTC/USD", TS_LOCAL)


def test_missing_asks_raises() -> None:
    raw = _book()
    del raw["asks"]
    with pytest.raises((ValueError, TypeError)):
        parse_cryptodotcom_book(raw, "BTC/USD", TS_LOCAL)


def test_empty_bids_raises() -> None:
    raw = _book()
    raw["bids"] = []
    with pytest.raises(ValueError):
        parse_cryptodotcom_book(raw, "BTC/USD", TS_LOCAL)


def test_empty_asks_raises() -> None:
    raw = _book()
    raw["asks"] = []
    with pytest.raises(ValueError):
        parse_cryptodotcom_book(raw, "BTC/USD", TS_LOCAL)


def test_timestamp_parsed_correctly() -> None:
    tob = parse_cryptodotcom_book(_book(ts=1772915676741), "BTC/USD", TS_LOCAL)
    assert tob.ts_exchange_ms == 1772915676741


def test_missing_timestamp_returns_none() -> None:
    raw = _book()
    del raw["t"]
    tob = parse_cryptodotcom_book(raw, "BTC/USD", TS_LOCAL)
    assert tob.ts_exchange_ms is None


def test_sol_btc_precision() -> None:
    """Test high-precision pair (7 decimal places)."""
    raw = _book(
        bid_px="0.0012320",
        bid_sz="0.721",
        ask_px="0.0012321",
        ask_sz="0.721",
    )
    tob = parse_cryptodotcom_book(raw, "SOL/BTC", TS_LOCAL)
    assert tob.bid_px == Decimal("0.0012320")
    assert tob.ask_px == Decimal("0.0012321")


def test_string_values_converted_to_decimal() -> None:
    """Crypto.com sends prices/sizes as strings — verify Decimal conversion."""
    tob = parse_cryptodotcom_book(_book(), "BTC/USD", TS_LOCAL)
    # If these were float, we'd get imprecision artifacts
    assert str(tob.bid_px) == "67276.63"
    assert str(tob.ask_sz) == "0.49833"
