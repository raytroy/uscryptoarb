from __future__ import annotations

from decimal import Decimal

import pytest

from tests.helpers import load_fixture
from uscryptoarb.connectors.okx.parser import parse_batch_tickers, parse_okx_ticker
from uscryptoarb.connectors.okx.symbols import OKX_SYMBOLS


def test_parse_okx_ticker_btc_usd_happy_path() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    item = raw["data"][0]
    tob = parse_okx_ticker(item, "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "okx"
    assert tob.pair == "BTC/USD"
    assert tob.bid_px == Decimal("68609.3")
    assert tob.bid_sz == Decimal("1.56258257")
    assert tob.ask_px == Decimal("68609.4")
    assert tob.ask_sz == Decimal("1.46068671")
    assert tob.ts_local_ms == 12345
    assert tob.ts_exchange_ms == 1771282524012


def test_parse_okx_ticker_sol_btc_precision() -> None:
    raw = load_fixture("okx_ticker_sol_btc.json")
    tob = parse_okx_ticker(raw["data"][0], "SOL/BTC", ts_local_ms=12345)
    assert tob.bid_px == Decimal("0.0012513")
    assert tob.ask_px == Decimal("0.0012516")


def test_parse_okx_ticker_returns_decimal_types() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    tob = parse_okx_ticker(raw["data"][0], "BTC/USD", ts_local_ms=12345)
    assert isinstance(tob.bid_px, Decimal)
    assert isinstance(tob.ask_px, Decimal)
    assert isinstance(tob.bid_sz, Decimal)
    assert isinstance(tob.ask_sz, Decimal)


def test_parse_okx_ticker_bid_less_than_ask() -> None:
    for fixture_name, pair in [
        ("okx_ticker_btc_usd.json", "BTC/USD"),
        ("okx_ticker_sol_btc.json", "SOL/BTC"),
    ]:
        raw = load_fixture(fixture_name)
        tob = parse_okx_ticker(raw["data"][0], pair, ts_local_ms=12345)
        assert tob.bid_px < tob.ask_px


def test_parse_okx_ticker_timestamp_already_ms() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    tob = parse_okx_ticker(raw["data"][0], "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms == 1771282524012


def test_parse_okx_ticker_venue_is_okx() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    tob = parse_okx_ticker(raw["data"][0], "BTC/USD", ts_local_ms=12345)
    assert tob.venue == "okx"


def test_parse_okx_ticker_ts_local_ms_passed_through() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    tob = parse_okx_ticker(raw["data"][0], "BTC/USD", ts_local_ms=99999)
    assert tob.ts_local_ms == 99999


def test_parse_okx_ticker_missing_ts_succeeds() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    item = dict(raw["data"][0])
    item.pop("ts")
    tob = parse_okx_ticker(item, "BTC/USD", ts_local_ms=12345)
    assert tob.ts_exchange_ms is None


def test_parse_okx_ticker_missing_bidpx_raises_keyerror() -> None:
    raw = load_fixture("okx_ticker_btc_usd.json")
    item = dict(raw["data"][0])
    item.pop("bidPx")
    with pytest.raises(KeyError):
        parse_okx_ticker(item, "BTC/USD", ts_local_ms=12345)


def test_parse_batch_tickers_happy_path_two_pairs() -> None:
    btc_item = load_fixture("okx_ticker_btc_usd.json")["data"][0]
    sol_item = load_fixture("okx_ticker_sol_btc.json")["data"][0]
    raw = {"code": "0", "msg": "", "data": [btc_item, sol_item]}

    out = parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)

    assert set(out.keys()) == {"BTC/USD", "SOL/BTC"}


def test_parse_batch_tickers_filters_unknown_symbols() -> None:
    btc_item = load_fixture("okx_ticker_btc_usd.json")["data"][0]
    unknown = {
        "instId": "DOGE-USD",
        "bidPx": "1",
        "bidSz": "1",
        "askPx": "2",
        "askSz": "1",
        "ts": "1771282524012",
    }
    raw = {"code": "0", "msg": "", "data": [btc_item, unknown]}

    out = parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)

    assert set(out.keys()) == {"BTC/USD"}


def test_parse_batch_tickers_nonzero_code_raises() -> None:
    raw = load_fixture("okx_error_invalid_instrument.json")
    with pytest.raises(ValueError, match="OKX API error"):
        parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)


def test_parse_batch_tickers_empty_data_raises() -> None:
    raw = {"code": "0", "msg": "", "data": []}
    with pytest.raises(ValueError, match="OKX tickers data"):
        parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)


def test_parse_batch_tickers_missing_data_key_raises() -> None:
    raw = {"code": "0", "msg": ""}
    with pytest.raises(ValueError, match="OKX tickers data"):
        parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)


def test_parse_batch_tickers_malformed_item_skips_and_parses_valid() -> None:
    btc_item = load_fixture("okx_ticker_btc_usd.json")["data"][0]
    bad_sol = dict(load_fixture("okx_ticker_sol_btc.json")["data"][0])
    bad_sol.pop("askPx")
    raw = {"code": "0", "msg": "", "data": [btc_item, bad_sol]}

    out = parse_batch_tickers(raw, ts_local_ms=12345, symbols=OKX_SYMBOLS)

    assert set(out.keys()) == {"BTC/USD"}
