import json
from decimal import Decimal
from pathlib import Path

import pytest

from uscryptoarb.connectors.gemini.parser import parse_book_response

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def test_parse_btc_usd_happy_path() -> None:
    raw = load_fixture("gemini_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "gemini"
    assert tob.pair == "BTC/USD"
    assert tob.bid_px == Decimal("68284.0")
    assert tob.bid_sz == Decimal("3.0")
    assert tob.ask_px == Decimal("68292.92")
    assert tob.ask_sz == Decimal("0.01538526")
    assert tob.ts_local_ms == 12345
    assert tob.ts_exchange_ms is not None


def test_parse_ltc_btc_precision() -> None:
    raw = load_fixture("gemini_book_ltc_btc.json")
    tob = parse_book_response(raw, "LTC/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.0007979")
    assert tob.ask_px == Decimal("0.0007988")


def test_parse_sol_btc_precision() -> None:
    raw = load_fixture("gemini_book_sol_btc.json")
    tob = parse_book_response(raw, "SOL/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.0012499")
    assert tob.ask_px == Decimal("0.0012506")
    assert tob.bid_sz == Decimal("1.349441")
    assert tob.ask_sz == Decimal("1.349441")


def test_parse_returns_decimal_types() -> None:
    raw = load_fixture("gemini_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_parse_bid_less_than_ask() -> None:
    for fixture_name, pair in [
        ("gemini_book_btc_usd.json", "BTC/USD"),
        ("gemini_book_ltc_btc.json", "LTC/BTC"),
        ("gemini_book_sol_btc.json", "SOL/BTC"),
    ]:
        raw = load_fixture(fixture_name)
        tob = parse_book_response(raw, pair, ts_local_ms=12345)
        assert tob.bid_px < tob.ask_px, f"bid >= ask for {fixture_name}"


def test_parse_timestamp_conversion() -> None:
    raw = load_fixture("gemini_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    # Fixture timestamp is "1771211101" -> 1771211101 * 1000
    assert tob.ts_exchange_ms == 1771211101 * 1000


def test_parse_timestamp_uses_max() -> None:
    raw = {
        "bids": [{"price": "100", "amount": "1", "timestamp": "1000"}],
        "asks": [{"price": "101", "amount": "1", "timestamp": "2000"}],
    }
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms == 2000 * 1000  # max(1000, 2000) * 1000


def test_parse_missing_timestamp_still_succeeds() -> None:
    raw = {
        "bids": [{"price": "100", "amount": "1"}],
        "asks": [{"price": "101", "amount": "1"}],
    }
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms is None


def test_parse_missing_bids_raises() -> None:
    raw = {"asks": [{"price": "1", "amount": "1", "timestamp": "100"}]}
    with pytest.raises(ValueError, match="bids"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_missing_asks_raises() -> None:
    raw = {"bids": [{"price": "1", "amount": "1", "timestamp": "100"}]}
    with pytest.raises(ValueError, match="asks"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_bids_raises() -> None:
    raw = {
        "bids": [],
        "asks": [{"price": "1", "amount": "1", "timestamp": "100"}],
    }
    with pytest.raises(ValueError, match="bids is empty"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_asks_raises() -> None:
    raw = {
        "bids": [{"price": "1", "amount": "1", "timestamp": "100"}],
        "asks": [],
    }
    with pytest.raises(ValueError, match="asks is empty"):
        parse_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_venue_is_gemini() -> None:
    raw = load_fixture("gemini_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "gemini"


def test_parse_ts_local_ms_passed_through() -> None:
    raw = load_fixture("gemini_book_btc_usd.json")
    tob = parse_book_response(raw, "BTC/USD", ts_local_ms=99999)
    assert tob.ts_local_ms == 99999
