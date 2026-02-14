import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from uscryptoarb.connectors.coinbase.parser import (
    _parse_iso_timestamp_ms,
    parse_product_book_response,
)

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def test_parse_btc_usd_happy_path() -> None:
    raw = load_fixture("coinbase_product_book_btc_usd.json")
    tob = parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "coinbase"
    assert tob.pair == "BTC/USD"
    assert tob.bid_px == Decimal("69845.94")
    assert tob.bid_sz == Decimal("0.08400565")
    assert tob.ask_px == Decimal("69845.95")
    assert tob.ask_sz == Decimal("0.10558907")
    assert tob.ts_local_ms == 12345
    assert tob.ts_exchange_ms is not None


def test_parse_ltc_btc_precision() -> None:
    raw = load_fixture("coinbase_product_book_ltc_btc.json")
    tob = parse_product_book_response(raw, "LTC/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.000811")
    assert tob.ask_px == Decimal("0.000812")


def test_parse_sol_btc_precision() -> None:
    raw = load_fixture("coinbase_product_book_sol_btc.json")
    tob = parse_product_book_response(raw, "SOL/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.0027451")
    assert tob.ask_px == Decimal("0.0027468")
    assert tob.bid_sz == Decimal("12.100")
    assert tob.ask_sz == Decimal("8.500")


def test_parse_returns_decimal_types() -> None:
    raw = load_fixture("coinbase_product_book_btc_usd.json")
    tob = parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_parse_bid_less_than_ask() -> None:
    for fixture_name in [
        "coinbase_product_book_btc_usd.json",
        "coinbase_product_book_ltc_btc.json",
        "coinbase_product_book_sol_btc.json",
    ]:
        raw = load_fixture(fixture_name)
        pair = raw["pricebook"]["product_id"].replace("-", "/")
        tob = parse_product_book_response(raw, pair, ts_local_ms=12345)
        assert tob.bid_px < tob.ask_px, f"bid >= ask for {fixture_name}"


def test_parse_iso_timestamp_ms() -> None:
    ts = _parse_iso_timestamp_ms("2026-02-14T17:23:44.194522Z")
    expected = int(datetime(2026, 2, 14, 17, 23, 44, 194522, tzinfo=UTC).timestamp() * 1000)
    assert ts == expected


def test_parse_iso_timestamp_ms_no_microseconds() -> None:
    ts = _parse_iso_timestamp_ms("2026-02-14T17:23:44Z")
    expected = int(datetime(2026, 2, 14, 17, 23, 44, tzinfo=UTC).timestamp() * 1000)
    assert ts == expected


def test_parse_exchange_timestamp_present() -> None:
    raw = load_fixture("coinbase_product_book_btc_usd.json")
    tob = parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms is not None
    assert tob.ts_exchange_ms > 0


def test_parse_missing_pricebook_raises() -> None:
    with pytest.raises(ValueError, match="pricebook"):
        parse_product_book_response({}, "BTC/USD", ts_local_ms=12345)


def test_parse_missing_bids_raises() -> None:
    raw = {
        "pricebook": {
            "asks": [{"price": "1", "size": "1"}],
            "time": "2026-01-01T00:00:00Z",
        }
    }
    with pytest.raises(ValueError, match="bids"):
        parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_missing_asks_raises() -> None:
    raw = {
        "pricebook": {
            "bids": [{"price": "1", "size": "1"}],
            "time": "2026-01-01T00:00:00Z",
        }
    }
    with pytest.raises(ValueError, match="asks"):
        parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_bids_raises() -> None:
    raw = {
        "pricebook": {
            "bids": [],
            "asks": [{"price": "1", "size": "1"}],
            "time": "2026-01-01T00:00:00Z",
        }
    }
    with pytest.raises(ValueError, match="bids is empty"):
        parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_empty_asks_raises() -> None:
    raw = {
        "pricebook": {
            "bids": [{"price": "1", "size": "1"}],
            "asks": [],
            "time": "2026-01-01T00:00:00Z",
        }
    }
    with pytest.raises(ValueError, match="asks is empty"):
        parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)


def test_parse_missing_timestamp_still_succeeds() -> None:
    raw = {
        "pricebook": {
            "bids": [{"price": "100", "size": "1"}],
            "asks": [{"price": "101", "size": "1"}],
        }
    }
    tob = parse_product_book_response(raw, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms is None
