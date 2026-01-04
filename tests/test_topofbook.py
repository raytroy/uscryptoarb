from decimal import Decimal

import pytest

from uscryptoarb.marketdata.topofbook import tob_from_raw


def test_tob_happy_path() -> None:
    t = tob_from_raw(
        venue="kraken",
        pair="BTC/USD",
        ts_local_ms=1_700_000_000_000,
        ts_exchange_ms=None,
        bid_px="43000.00",
        bid_sz="0.50",
        ask_px="43001.00",
        ask_sz="0.40",
    )
    assert t.bid_px == Decimal("43000.00")
    assert t.ask_px == Decimal("43001.00")


def test_tob_rejects_crossed_book() -> None:
    with pytest.raises(ValueError):
        tob_from_raw(
            venue="kraken",
            pair="BTC/USD",
            ts_local_ms=1,
            ts_exchange_ms=None,
            bid_px="100",
            bid_sz="1",
            ask_px="99",
            ask_sz="1",
        )
