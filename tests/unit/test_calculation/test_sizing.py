"""Tests for calculation/sizing.py.

Verifies Kelly Criterion math against hand-calculated examples
matching the Mathematica CalcKellyAmount[] function.
"""

from decimal import Decimal

import pytest

from uscryptoarb.calculation.sizing import (
    DEFAULT_KELLY_MULTIPLIER,
    DEFAULT_PROB_SUCCESS,
    calc_kelly_amount,
    calc_kelly_fraction,
    calc_position_size,
)
from uscryptoarb.calculation.types import TradingAccuracy


class TestCalcKellyFraction:
    def test_positive_edge(self) -> None:
        result = calc_kelly_fraction(
            edge=Decimal("0.0025"),
            prob_success=Decimal("0.95"),
        )
        assert result == Decimal("0.002375")

    def test_zero_edge_returns_zero(self) -> None:
        result = calc_kelly_fraction(Decimal("0"), Decimal("0.95"))
        assert result == Decimal("0")

    def test_negative_edge_returns_zero(self) -> None:
        result = calc_kelly_fraction(Decimal("-0.001"), Decimal("0.95"))
        assert result == Decimal("0")

    def test_perfect_probability(self) -> None:
        result = calc_kelly_fraction(Decimal("0.01"), Decimal("1.0"))
        assert result == Decimal("0.01")


class TestCalcKellyAmount:
    def test_golden_example(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.008"),
            threshold=Decimal("0.0055"),
            prob_success=Decimal("0.95"),
            kelly_multiplier=Decimal("0.25"),
        )
        assert result == Decimal("0.59375")

    def test_uses_default_params(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.008"),
            threshold=Decimal("0.0055"),
        )
        assert result == Decimal("0.59375")
        assert DEFAULT_PROB_SUCCESS == Decimal("0.95")
        assert DEFAULT_KELLY_MULTIPLIER == Decimal("0.25")

    def test_below_threshold_returns_zero(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.005"),
            threshold=Decimal("0.0055"),
        )
        assert result == Decimal("0")

    def test_exactly_at_threshold_returns_zero(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.0055"),
            threshold=Decimal("0.0055"),
        )
        assert result == Decimal("0")

    def test_max_fraction_cap(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.50"),
            threshold=Decimal("0.0055"),
            prob_success=Decimal("0.95"),
            kelly_multiplier=Decimal("1.0"),
            max_fraction=Decimal("0.10"),
        )
        assert result == Decimal("100")

    def test_custom_max_fraction(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("1000"),
            return_grs=Decimal("0.50"),
            threshold=Decimal("0.0055"),
            max_fraction=Decimal("0.05"),
        )
        assert result == Decimal("50")

    def test_large_bankroll(self) -> None:
        result = calc_kelly_amount(
            bankroll=Decimal("100000"),
            return_grs=Decimal("0.008"),
            threshold=Decimal("0.0055"),
        )
        assert result == Decimal("59.375")


class TestCalcPositionSize:
    @pytest.fixture()
    def kraken_accuracy(self) -> TradingAccuracy:
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

    def test_basic_conversion(self, kraken_accuracy: TradingAccuracy) -> None:
        result = calc_position_size(
            kelly_amount_base=Decimal("59.375"),
            price=Decimal("69113.0"),
            accuracy=kraken_accuracy,
        )
        assert result > Decimal("0")
        assert result >= kraken_accuracy.min_order_size

    def test_below_min_order_returns_zero(self, kraken_accuracy: TradingAccuracy) -> None:
        result = calc_position_size(
            kelly_amount_base=Decimal("0.001"),
            price=Decimal("69113.0"),
            accuracy=kraken_accuracy,
        )
        assert result == Decimal("0")

    def test_respects_max_order_size(self) -> None:
        coinbase_accuracy = TradingAccuracy(
            venue="coinbase",
            pair="BTC/USD",
            price_decimals=2,
            lot_decimals=8,
            min_order_size=Decimal("0.00000001"),
            max_order_size=Decimal("3500"),
            tick_size=Decimal("0.01"),
            lot_step=Decimal("0.00000001"),
        )
        result = calc_position_size(
            kelly_amount_base=Decimal("500000000"),
            price=Decimal("69113.0"),
            accuracy=coinbase_accuracy,
        )
        assert result <= Decimal("3500")

    def test_floors_to_lot_step(self) -> None:
        acc = TradingAccuracy(
            venue="test",
            pair="SOL/BTC",
            price_decimals=7,
            lot_decimals=3,
            min_order_size=Decimal("0.001"),
            max_order_size=None,
            tick_size=Decimal("0.0000001"),
            lot_step=Decimal("0.001"),
        )
        result = calc_position_size(
            kelly_amount_base=Decimal("0.005"),
            price=Decimal("0.0025"),
            accuracy=acc,
        )
        assert result % Decimal("0.001") == Decimal("0")
