"""Shared fixtures for calculation layer tests.

All fixtures use deterministic Decimal values — no randomness,
no live network (DEC-007, LL-010).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from uscryptoarb.calculation.types import (
    FeeSchedule,
    TradingAccuracy,
    TradingFeeRate,
    WithdrawalFee,
)
from uscryptoarb.marketdata.topofbook import TopOfBook

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

    Higher prices than Kraken → buy on Kraken, sell on Coinbase.
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


# ---------------------------------------------------------------------------
# Fee fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kraken_fee_rate() -> TradingFeeRate:
    """Kraken taker fee: 0.26%."""
    return TradingFeeRate(
        venue="kraken",
        action="buy",
        pct_fee=Decimal("0.0026"),
        flat_fee=Decimal("0"),
    )


@pytest.fixture()
def coinbase_fee_rate() -> TradingFeeRate:
    """Coinbase taker fee: 0.60%."""
    return TradingFeeRate(
        venue="coinbase",
        action="buy",
        pct_fee=Decimal("0.006"),
        flat_fee=Decimal("0"),
    )


@pytest.fixture()
def kraken_btc_withdrawal() -> WithdrawalFee:
    """Kraken BTC withdrawal: ~0.00005 BTC."""
    return WithdrawalFee(
        venue="kraken",
        currency="BTC",
        flat_fee=Decimal("0.00005"),
        pct_fee=Decimal("0"),
    )


@pytest.fixture()
def coinbase_usd_withdrawal() -> WithdrawalFee:
    """Coinbase USD withdrawal: free."""
    return WithdrawalFee(
        venue="coinbase",
        currency="USD",
        flat_fee=Decimal("0"),
        pct_fee=Decimal("0"),
    )


@pytest.fixture()
def kraken_btc_usd_accuracy() -> TradingAccuracy:
    """Kraken BTC/USD precision from AssetPairs API."""
    return TradingAccuracy(
        venue="kraken",
        pair="BTC/USD",
        price_decimals=1,
        lot_decimals=8,
        min_order_size=Decimal("0.00005"),
        max_order_size=None,
        tick_size=Decimal("0.1"),
        lot_step=Decimal("0.00000001"),
    )


@pytest.fixture()
def coinbase_btc_usd_accuracy() -> TradingAccuracy:
    """Coinbase BTC/USD precision from Products API."""
    return TradingAccuracy(
        venue="coinbase",
        pair="BTC/USD",
        price_decimals=2,
        lot_decimals=8,
        min_order_size=Decimal("0.00000001"),
        max_order_size=Decimal("3500"),
        tick_size=Decimal("0.01"),
        lot_step=Decimal("0.00000001"),
    )


@pytest.fixture()
def kraken_btc_usd_fees(
    kraken_fee_rate: TradingFeeRate,
    kraken_btc_withdrawal: WithdrawalFee,
    kraken_btc_usd_accuracy: TradingAccuracy,
) -> FeeSchedule:
    """Full Kraken BTC/USD fee schedule.

    Buy withdrawal = BTC withdrawal (you might move BTC off Kraken).
    Sell withdrawal = None (you receive USD on Kraken, no withdrawal modeled).
    """
    return FeeSchedule(
        buy_fee=kraken_fee_rate,
        sell_fee=TradingFeeRate(
            venue="kraken",
            action="sell",
            pct_fee=Decimal("0.0026"),
            flat_fee=Decimal("0"),
        ),
        buy_withdrawal=kraken_btc_withdrawal,
        sell_withdrawal=None,
        accuracy=kraken_btc_usd_accuracy,
    )


@pytest.fixture()
def coinbase_btc_usd_fees(
    coinbase_fee_rate: TradingFeeRate,
    coinbase_usd_withdrawal: WithdrawalFee,
    coinbase_btc_usd_accuracy: TradingAccuracy,
) -> FeeSchedule:
    """Full Coinbase BTC/USD fee schedule.

    Buy withdrawal = None (no need to move BTC off Coinbase for arb).
    Sell withdrawal = USD withdrawal (free on Coinbase).
    """
    return FeeSchedule(
        buy_fee=coinbase_fee_rate,
        sell_fee=TradingFeeRate(
            venue="coinbase",
            action="sell",
            pct_fee=Decimal("0.006"),
            flat_fee=Decimal("0"),
        ),
        buy_withdrawal=None,
        sell_withdrawal=coinbase_usd_withdrawal,
        accuracy=coinbase_btc_usd_accuracy,
    )
