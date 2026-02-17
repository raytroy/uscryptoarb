"""Shared test fixtures for all test packages.

JSON fixture loaders for connector tests, plus TopOfBook and FeeSchedule
fixtures used by both test_calculation/ and test_strategy/.

All fixtures use deterministic Decimal values — no randomness,
no live network (DEC-007, LL-010).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.helpers import load_fixture
from uscryptoarb.calculation.calc_types import (
    FeeSchedule,
    TradingAccuracy,
    TradingFeeRate,
    WithdrawalFee,
)
from uscryptoarb.marketdata.topofbook import TopOfBook

# ---------------------------------------------------------------------------
# JSON fixture loaders (for connector tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def kraken_ticker_fixture() -> dict:
    return load_fixture("kraken_ticker_response.json")


@pytest.fixture
def kraken_orderbook_fixture() -> dict:
    return load_fixture("kraken_orderbook_response.json")


@pytest.fixture
def kraken_asset_pairs_fixture() -> dict:
    return load_fixture("kraken_asset_pairs_btcusd.json")


@pytest.fixture
def coinbase_product_book_btc_usd_fixture() -> dict:
    return load_fixture("coinbase_product_book_btc_usd.json")


@pytest.fixture
def coinbase_product_book_ltc_btc_fixture() -> dict:
    return load_fixture("coinbase_product_book_ltc_btc.json")


@pytest.fixture
def coinbase_product_book_sol_btc_fixture() -> dict:
    return load_fixture("coinbase_product_book_sol_btc.json")


@pytest.fixture
def gemini_book_btc_usd_fixture() -> dict:
    return load_fixture("gemini_book_btc_usd.json")


@pytest.fixture
def gemini_book_ltc_btc_fixture() -> dict:
    return load_fixture("gemini_book_ltc_btc.json")


@pytest.fixture
def gemini_book_sol_btc_fixture() -> dict:
    return load_fixture("gemini_book_sol_btc.json")


@pytest.fixture
def bitstamp_book_btc_usd_fixture() -> dict:
    return load_fixture("bitstamp_book_btc_usd.json")


@pytest.fixture
def bitstamp_book_ltc_btc_fixture() -> dict:
    return load_fixture("bitstamp_book_ltc_btc.json")


@pytest.fixture
def bitstamp_book_btc_usdc_fixture() -> dict:
    return load_fixture("bitstamp_book_btc_usdc.json")


# ---------------------------------------------------------------------------
# TopOfBook fixtures — deterministic BTC/USD snapshots
# ---------------------------------------------------------------------------


@pytest.fixture()
def kraken_btc_usd_tob() -> TopOfBook:
    """Kraken BTC/USD: bid 69100.0, ask 69113.0."""
    return TopOfBook(
        venue="kraken",
        pair="BTC/USD",
        ts_local_ms=1707900000000,
        ts_exchange_ms=None,
        bid_px=Decimal("69100.0"),
        bid_sz=Decimal("1.5"),
        ask_px=Decimal("69113.0"),
        ask_sz=Decimal("2.0"),
    )


@pytest.fixture()
def coinbase_btc_usd_tob() -> TopOfBook:
    """Coinbase BTC/USD: bid 69200.0, ask 69220.0.

    Higher prices than Kraken -> buy on Kraken, sell on Coinbase.
    """
    return TopOfBook(
        venue="coinbase",
        pair="BTC/USD",
        ts_local_ms=1707900000000,
        ts_exchange_ms=1707900000000,
        bid_px=Decimal("69200.0"),
        bid_sz=Decimal("1.0"),
        ask_px=Decimal("69220.0"),
        ask_sz=Decimal("1.5"),
    )


@pytest.fixture()
def gemini_btc_usd_tob() -> TopOfBook:
    """Gemini BTC/USD: bid 69150.0, ask 69165.0.

    Priced between Kraken and Coinbase for 3-exchange tests.
    """
    return TopOfBook(
        venue="gemini",
        pair="BTC/USD",
        ts_local_ms=1707900000000,
        ts_exchange_ms=1707900000000,
        bid_px=Decimal("69150.0"),
        bid_sz=Decimal("0.8"),
        ask_px=Decimal("69165.0"),
        ask_sz=Decimal("1.2"),
    )


@pytest.fixture()
def kraken_btc_usd_tob_inverted() -> TopOfBook:
    """Kraken BTC/USD with HIGHER prices than Coinbase.

    For testing sell-on-Kraken direction.
    """
    return TopOfBook(
        venue="kraken",
        pair="BTC/USD",
        ts_local_ms=1707900000000,
        ts_exchange_ms=None,
        bid_px=Decimal("69250.0"),
        bid_sz=Decimal("1.5"),
        ask_px=Decimal("69260.0"),
        ask_sz=Decimal("2.0"),
    )


@pytest.fixture()
def stale_tob() -> TopOfBook:
    """A TopOfBook with ts_local_ms far in the past (for staleness tests)."""
    return TopOfBook(
        venue="stale_exchange",
        pair="BTC/USD",
        ts_local_ms=1707800000000,  # 100_000_000ms before standard fixtures
        ts_exchange_ms=None,
        bid_px=Decimal("69000.0"),
        bid_sz=Decimal("1.0"),
        ask_px=Decimal("69050.0"),
        ask_sz=Decimal("1.0"),
    )


# ---------------------------------------------------------------------------
# Fee fixtures — factory + named wrappers for backward compatibility
# ---------------------------------------------------------------------------


@pytest.fixture()
def fee_schedule_factory():
    """Factory for building FeeSchedule with explicit per-field control.

    All string amounts are converted to Decimal for determinism (LL-010).
    Named fixtures below are thin wrappers for backward compatibility.
    """

    def _make(
        *,
        venue: str,
        pair: str = "BTC/USD",
        buy_pct: str = "0.0040",
        sell_pct: str = "0.0040",
        buy_flat: str = "0",
        sell_flat: str = "0",
        buy_withdrawal_currency: str | None = None,
        buy_withdrawal_flat: str = "0",
        buy_withdrawal_pct: str = "0",
        sell_withdrawal_currency: str | None = None,
        sell_withdrawal_flat: str = "0",
        sell_withdrawal_pct: str = "0",
        price_decimals: int = 2,
        lot_decimals: int = 8,
        min_order_size: str = "0.00001",
        max_order_size: str | None = None,
        tick_size: str = "0.01",
        lot_step: str = "0.00000001",
    ) -> FeeSchedule:
        buy_wd = (
            WithdrawalFee(
                venue=venue,
                currency=buy_withdrawal_currency,
                flat_fee=Decimal(buy_withdrawal_flat),
                pct_fee=Decimal(buy_withdrawal_pct),
            )
            if buy_withdrawal_currency is not None
            else None
        )

        sell_wd = (
            WithdrawalFee(
                venue=venue,
                currency=sell_withdrawal_currency,
                flat_fee=Decimal(sell_withdrawal_flat),
                pct_fee=Decimal(sell_withdrawal_pct),
            )
            if sell_withdrawal_currency is not None
            else None
        )

        return FeeSchedule(
            buy_fee=TradingFeeRate(
                venue=venue,
                action="buy",
                pct_fee=Decimal(buy_pct),
                flat_fee=Decimal(buy_flat),
            ),
            sell_fee=TradingFeeRate(
                venue=venue,
                action="sell",
                pct_fee=Decimal(sell_pct),
                flat_fee=Decimal(sell_flat),
            ),
            buy_withdrawal=buy_wd,
            sell_withdrawal=sell_wd,
            accuracy=TradingAccuracy(
                venue=venue,
                pair=pair,
                price_decimals=price_decimals,
                lot_decimals=lot_decimals,
                min_order_size=Decimal(min_order_size),
                max_order_size=Decimal(max_order_size) if max_order_size is not None else None,
                tick_size=Decimal(tick_size),
                lot_step=Decimal(lot_step),
            ),
        )

    return _make


@pytest.fixture()
def kraken_btc_usd_fees(fee_schedule_factory) -> FeeSchedule:
    """Full Kraken BTC/USD fee schedule.

    Buy withdrawal = BTC withdrawal (you might move BTC off Kraken).
    Sell withdrawal = None (you receive USD on Kraken, no withdrawal modeled).
    """
    return fee_schedule_factory(
        venue="kraken",
        pair="BTC/USD",
        buy_pct="0.0040",
        sell_pct="0.0040",
        buy_withdrawal_currency="BTC",
        buy_withdrawal_flat="0.00001",
        buy_withdrawal_pct="0",
        # sell_withdrawal = None (no currency -> None)
        price_decimals=1,
        lot_decimals=8,
        min_order_size="0.00005",
        tick_size="0.1",
        lot_step="0.00000001",
    )


@pytest.fixture()
def coinbase_btc_usd_fees(fee_schedule_factory) -> FeeSchedule:
    """Full Coinbase BTC/USD fee schedule.

    Buy withdrawal = None (no need to move BTC off Coinbase for arb).
    Sell withdrawal = USD withdrawal (free on Coinbase).
    """
    return fee_schedule_factory(
        venue="coinbase",
        pair="BTC/USD",
        buy_pct="0.012",
        sell_pct="0.012",
        # buy_withdrawal = None (no currency -> None)
        sell_withdrawal_currency="USD",
        sell_withdrawal_flat="0",
        sell_withdrawal_pct="0",
        price_decimals=2,
        lot_decimals=8,
        min_order_size="0.00000001",
        max_order_size="3500",
        tick_size="0.01",
        lot_step="0.00000001",
    )


@pytest.fixture()
def gemini_btc_usd_fees(fee_schedule_factory) -> FeeSchedule:
    """Full Gemini BTC/USD fee schedule.

    Gemini taker: 0.40%. Free withdrawals for both sides.
    """
    return fee_schedule_factory(
        venue="gemini",
        pair="BTC/USD",
        buy_pct="0.004",
        sell_pct="0.004",
        # buy_withdrawal = None, sell_withdrawal = None
        price_decimals=2,
        lot_decimals=8,
        min_order_size="0.00001",
        tick_size="0.01",
        lot_step="0.00000001",
    )
