import json
from decimal import Decimal
from pathlib import Path

import pytest

from uscryptoarb.connectors.kraken.parser import parse_orderbook_response, parse_ticker_response
from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOLS

FIXTURES = Path(__file__).resolve().parents[4] / "fixtures"


def load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def test_parse_ticker_happy_path() -> None:
    raw = load_fixture("kraken_ticker_response.json")
    out = parse_ticker_response(raw, ts_local_ms=12345, symbols=KRAKEN_SYMBOLS)
    assert len(out) == 8


def test_parse_ticker_returns_decimal_types() -> None:
    out = parse_ticker_response(load_fixture("kraken_ticker_response.json"), 12345, KRAKEN_SYMBOLS)
    tob = out["BTC/USD"]
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.ask_px, Decimal)


def test_parse_ticker_bid_less_than_ask() -> None:
    out = parse_ticker_response(load_fixture("kraken_ticker_response.json"), 12345, KRAKEN_SYMBOLS)
    assert all(tob.bid_px < tob.ask_px for tob in out.values())


def test_parse_ticker_skips_unknown_symbol() -> None:
    raw = load_fixture("kraken_ticker_response.json")
    raw["UNKNOWN"] = raw["XXBTZUSD"]
    out = parse_ticker_response(raw, 12345, KRAKEN_SYMBOLS)
    assert "UNKNOWN" not in out
    assert len(out) == 8


def test_parse_ticker_skips_invalid_data() -> None:
    raw = load_fixture("kraken_ticker_response.json")
    raw["XXBTZUSD"] = {"a": ["1", "1", "1"]}
    out = parse_ticker_response(raw, 12345, KRAKEN_SYMBOLS)
    assert "BTC/USD" not in out


def test_parse_ticker_empty_result() -> None:
    assert parse_ticker_response({}, 12345, KRAKEN_SYMBOLS) == {}


def test_parse_orderbook_happy_path() -> None:
    raw = load_fixture("kraken_orderbook_response.json")
    out = parse_orderbook_response(raw, "BTC/USD", "XXBTZUSD", 12345)
    assert out.pair == "BTC/USD"
    assert out.venue == "kraken"
    assert out.ts_exchange_ms is not None


def test_parse_orderbook_timestamp_conversion() -> None:
    raw = load_fixture("kraken_orderbook_response.json")
    out = parse_orderbook_response(raw, "BTC/USD", "XXBTZUSD", 12345)
    assert out.ts_exchange_ms == 1771008952000


def test_parse_orderbook_empty_asks_raises() -> None:
    raw = {"XXBTZUSD": {"asks": [], "bids": [["1", "1", 1]]}}
    with pytest.raises(ValueError):
        parse_orderbook_response(raw, "BTC/USD", "XXBTZUSD", 1)


def test_parse_orderbook_empty_bids_raises() -> None:
    raw = {"XXBTZUSD": {"asks": [["1", "1", 1]], "bids": []}}
    with pytest.raises(ValueError):
        parse_orderbook_response(raw, "BTC/USD", "XXBTZUSD", 1)


def test_parse_orderbook_missing_key_raises() -> None:
    with pytest.raises(ValueError):
        parse_orderbook_response({}, "BTC/USD", "XXBTZUSD", 1)


def test_parse_ticker_venue_is_kraken() -> None:
    out = parse_ticker_response(load_fixture("kraken_ticker_response.json"), 12345, KRAKEN_SYMBOLS)
    assert all(t.venue == "kraken" for t in out.values())


def test_parse_ticker_pair_is_canonical() -> None:
    out = parse_ticker_response(load_fixture("kraken_ticker_response.json"), 12345, KRAKEN_SYMBOLS)
    assert "BTC/USD" in out
    assert "XXBTZUSD" not in out
