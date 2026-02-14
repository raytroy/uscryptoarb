"""Tests for calculation/returns.py.

All tests use deterministic Decimal values.
Naming: test_<function>_<scenario>_<expected>.
"""

from decimal import Decimal

from uscryptoarb.calculation.returns import (
    calc_profit_base,
    calc_return_grs,
    calc_return_net,
    calc_return_raw,
)


class TestCalcReturnRaw:
    def test_positive_spread_returns_positive(self) -> None:
        """Sell higher than buy → positive return."""
        result = calc_return_raw(
            buy_price=Decimal("69113.0"),
            sell_price=Decimal("69200.0"),
        )
        assert result > Decimal("0")
        assert result == Decimal("87") / Decimal("69113")

    def test_negative_spread_returns_negative(self) -> None:
        """Sell lower than buy → negative return (no arb)."""
        result = calc_return_raw(
            buy_price=Decimal("69200.0"),
            sell_price=Decimal("69100.0"),
        )
        assert result < Decimal("0")

    def test_equal_prices_returns_zero(self) -> None:
        """Same price → zero return."""
        result = calc_return_raw(
            buy_price=Decimal("69113.0"),
            sell_price=Decimal("69113.0"),
        )
        assert result == Decimal("0")

    def test_known_value_btc(self) -> None:
        """Hand-calculated BTC example matching expected precision."""
        result = calc_return_raw(Decimal("69113"), Decimal("69200"))
        expected = Decimal("87") / Decimal("69113")
        assert result == expected

    def test_small_spread_ltc(self) -> None:
        """LTC with small spread — still positive."""
        result = calc_return_raw(Decimal("105.50"), Decimal("105.60"))
        expected = Decimal("0.10") / Decimal("105.50")
        assert result == expected


class TestCalcReturnGrs:
    def test_positive_after_fees(self) -> None:
        """Gross return positive when spread exceeds fees."""
        buy_cost = Decimal("6929.2638")
        sell_proceeds = Decimal("6950.00")
        result = calc_return_grs(buy_cost, sell_proceeds)
        assert result > Decimal("0")

    def test_negative_when_fees_exceed_spread(self) -> None:
        """Negative return when fees eat the spread."""
        buy_cost = Decimal("6929.00")
        sell_proceeds = Decimal("6920.00")
        result = calc_return_grs(buy_cost, sell_proceeds)
        assert result < Decimal("0")


class TestCalcReturnNet:
    def test_net_less_than_gross(self) -> None:
        """Net return is always ≤ gross when withdrawal fees > 0."""
        buy_total = Decimal("6935.00")
        sell_net = Decimal("6945.00")
        gross_result = calc_return_grs(Decimal("6930.00"), Decimal("6950.00"))
        net_result = calc_return_net(buy_total, sell_net)
        assert net_result < gross_result

    def test_zero_withdrawal_equals_gross(self) -> None:
        """With zero withdrawal fees, net return equals gross return."""
        cost = Decimal("6930.00")
        proceeds = Decimal("6950.00")
        grs = calc_return_grs(cost, proceeds)
        net = calc_return_net(cost, proceeds)
        assert grs == net


class TestCalcProfitBase:
    def test_profitable_trade(self) -> None:
        result = calc_profit_base(Decimal("6930.00"), Decimal("6950.00"))
        assert result == Decimal("20.00")

    def test_unprofitable_trade(self) -> None:
        result = calc_profit_base(Decimal("6950.00"), Decimal("6930.00"))
        assert result == Decimal("-20.00")

    def test_breakeven(self) -> None:
        result = calc_profit_base(Decimal("6930.00"), Decimal("6930.00"))
        assert result == Decimal("0")
