"""Tests for connectors/bitstamp/parser.py — Bitstamp order book parsing.

Bitstamp order book entries are arrays-of-arrays (LL-070):
    [["price_str", "amount_str"], ...]
NOT arrays-of-objects like Gemini/Coinbase.

Timestamps use microtimestamp (Unix microseconds as string, LL-071).
"""

from decimal import Decimal

import pytest

from tests.helpers import load_fixture
from uscryptoarb.connectors.bitstamp.parser import parse_book_response

# ---------------------------------------------------------------------------
# Happy-path tests with fixtures
# ---------------------------------------------------------------------------


def test_parse_btc_usd_happy_path() -> None:
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.bid_px == Decimal("68665")
    assert tob.bid_sz == Decimal("1.40230385")
    assert tob.ask_px == Decimal("68666")
    assert tob.ask_sz == Decimal("0.15031007")


def test_parse_ltc_btc_precision() -> None:
    raw = load_fixture("bitstamp_book_ltc_btc.json")
    tob = parse_book_response(raw, "LTC/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.00080295")
    assert tob.bid_sz == Decimal("9.07187595")
    assert tob.ask_px == Decimal("0.00080418")
    assert tob.ask_sz == Decimal("30.14756511")


def test_parse_btc_usdc_precision() -> None:
    raw = load_fixture("bitstamp_book_btc_usdc.json")
    tob = parse_book_response(raw, "BTC/USDC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("68627")
    assert tob.ask_px == Decimal("68715")


# ---------------------------------------------------------------------------
# Type and invariant tests
# ---------------------------------------------------------------------------


def test_parse_returns_decimal_types() -> None:
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_parse_bid_less_than_ask() -> None:
    """All fixtures should have bid < ask (not crossed)."""
    for fixture_name in [
        "bitstamp_book_btc_usd.json",
        "bitstamp_book_ltc_btc.json",
        "bitstamp_book_btc_usdc.json",
    ]:
        raw = load_fixture(fixture_name)
        tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
        assert tob.bid_px < tob.ask_px, f"Crossed book in {fixture_name}"


# ---------------------------------------------------------------------------
# Timestamp tests (LL-071)
# ---------------------------------------------------------------------------


def test_parse_microtimestamp_conversion() -> None:
    """microtimestamp 1771281528771691 // 1000 == 1771281528771."""
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms == 1771281528771


def test_parse_timestamp_fallback() -> None:
    """When microtimestamp is missing, use timestamp * 1000."""
    raw = load_fixture("bitstamp_book_btc_usd.json")
    del raw["microtimestamp"]
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms == 1771281528000


def test_parse_missing_both_timestamps() -> None:
    """When both timestamps are missing, ts_exchange_ms is None."""
    raw = load_fixture("bitstamp_book_btc_usd.json")
    del raw["microtimestamp"]
    del raw["timestamp"]
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms is None


# ---------------------------------------------------------------------------
# Metadata tests
# ---------------------------------------------------------------------------


def test_parse_venue_is_bitstamp() -> None:
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "bitstamp"


def test_parse_ts_local_ms_passed_through() -> None:
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=99999)
    assert tob.ts_local_ms == 99999


def test_parse_pair_passed_through() -> None:
    raw = load_fixture("bitstamp_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.pair == "BTC/USD"


# ---------------------------------------------------------------------------
# Error-path tests
# ---------------------------------------------------------------------------


def test_parse_missing_bids_raises() -> None:
    raw = {"asks": [["1", "1"]], "timestamp": "100", "microtimestamp": "100000"}
    with pytest.raises(ValueError, match="bids"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_missing_asks_raises() -> None:
    raw = {"bids": [["1", "1"]], "timestamp": "100", "microtimestamp": "100000"}
    with pytest.raises(ValueError, match="asks"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_bids_raises() -> None:
    raw = {"bids": [], "asks": [["1", "1"]], "timestamp": "100"}
    with pytest.raises(ValueError, match="bids.*empty"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_asks_raises() -> None:
    raw = {"bids": [["1", "1"]], "asks": [], "timestamp": "100"}
    with pytest.raises(ValueError, match="asks.*empty"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
