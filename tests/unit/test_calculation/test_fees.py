"""Tests for calculation/fees.py.

Hand-calculated examples verify the Mathematica MktCurrAmt fee flow.
All values are deterministic Decimal — no floats (LL-010).
"""

from decimal import Decimal

from uscryptoarb.calculation.fees import (
    calc_buy_leg,
    calc_sell_leg,
    effective_buy_cost,
    effective_sell_proceeds,
    net_sell_proceeds,
    total_buy_cost,
)
from uscryptoarb.calculation.types import WithdrawalFee


class TestCalcBuyLeg:
    def test_basic_buy_no_withdrawal(self) -> None:
        leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
        )
        assert leg.venue == "kraken"
        assert leg.side == "buy"
        assert leg.price == Decimal("69113.0")
        assert leg.mkt_curr_amt == Decimal("0.1")
        assert leg.base_curr_amt == Decimal("6911.30")
        expected_fee = Decimal("6911.30") * Decimal("0.0026")
        assert leg.trading_fee_base == expected_fee
        assert leg.withdrawal_fee == Decimal("0")

    def test_buy_with_btc_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="kraken",
            currency="BTC",
            flat_fee=Decimal("0.00005"),
            pct_fee=Decimal("0"),
        )
        leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
            withdrawal=w,
        )
        assert leg.withdrawal_fee == Decimal("0.00005")

    def test_buy_with_pct_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="test",
            currency="BTC",
            flat_fee=Decimal("0.0001"),
            pct_fee=Decimal("0.001"),
        )
        leg = calc_buy_leg(
            venue="test",
            pair="BTC/USD",
            price=Decimal("69000"),
            amount=Decimal("1.0"),
            fee_pct=Decimal("0.0026"),
            withdrawal=w,
        )
        assert leg.withdrawal_fee == Decimal("0.0011")


class TestCalcSellLeg:
    def test_basic_sell_no_withdrawal(self) -> None:
        leg = calc_sell_leg(
            venue="coinbase",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.006"),
        )
        assert leg.venue == "coinbase"
        assert leg.side == "sell"
        assert leg.price == Decimal("69200.0")
        assert leg.mkt_curr_amt == Decimal("0.1")
        assert leg.base_curr_amt == Decimal("6920.00")
        expected_fee = Decimal("6920.00") * Decimal("0.006")
        assert leg.trading_fee_base == expected_fee
        assert leg.withdrawal_fee == Decimal("0")

    def test_sell_with_usd_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="coinbase",
            currency="USD",
            flat_fee=Decimal("0"),
            pct_fee=Decimal("0"),
        )
        leg = calc_sell_leg(
            venue="coinbase",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.006"),
            withdrawal=w,
        )
        assert leg.withdrawal_fee == Decimal("0")

    def test_sell_with_flat_usd_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="kraken",
            currency="USD",
            flat_fee=Decimal("5.00"),
            pct_fee=Decimal("0"),
        )
        leg = calc_sell_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
            withdrawal=w,
        )
        assert leg.withdrawal_fee == Decimal("5.00")


class TestEffectiveCosts:
    def test_effective_buy_cost_adds_fee(self) -> None:
        leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
        )
        cost = effective_buy_cost(leg)
        expected = Decimal("6911.30") * Decimal("1.0026")
        assert cost == expected

    def test_effective_sell_proceeds_subtracts_fee(self) -> None:
        leg = calc_sell_leg(
            venue="coinbase",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.006"),
        )
        proceeds = effective_sell_proceeds(leg)
        expected = Decimal("6920.00") * Decimal("0.994")
        assert proceeds == expected

    def test_fee_direction_buy_vs_sell(self) -> None:
        buy_leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
        )
        sell_leg = calc_sell_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
        )

        buy_cost = effective_buy_cost(buy_leg)
        sell_proceeds = effective_sell_proceeds(sell_leg)

        assert buy_cost > sell_proceeds
        raw_base = Decimal("0.1") * Decimal("69113.0")
        assert buy_cost > raw_base
        assert sell_proceeds < raw_base


class TestNetAmounts:
    def test_total_buy_cost_includes_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="kraken",
            currency="BTC",
            flat_fee=Decimal("0.00005"),
            pct_fee=Decimal("0"),
        )
        leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
            withdrawal=w,
        )
        total = total_buy_cost(leg)
        eff = effective_buy_cost(leg)

        withdrawal_in_base = Decimal("0.00005") * Decimal("69113.0")
        assert total == eff + withdrawal_in_base

    def test_net_sell_proceeds_subtracts_withdrawal(self) -> None:
        w = WithdrawalFee(
            venue="kraken",
            currency="USD",
            flat_fee=Decimal("5.00"),
            pct_fee=Decimal("0"),
        )
        leg = calc_sell_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
            withdrawal=w,
        )
        net = net_sell_proceeds(leg)
        eff = effective_sell_proceeds(leg)
        assert net == eff - Decimal("5.00")

    def test_no_withdrawal_total_equals_effective(self) -> None:
        leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=Decimal("0.1"),
            fee_pct=Decimal("0.0026"),
        )
        assert total_buy_cost(leg) == effective_buy_cost(leg)


class TestGoldenFeeFlow:
    def test_golden_buy_sell_flow(self) -> None:
        kraken_w = WithdrawalFee(
            venue="kraken",
            currency="BTC",
            flat_fee=Decimal("0.00005"),
            pct_fee=Decimal("0"),
        )
        coinbase_w = WithdrawalFee(
            venue="coinbase",
            currency="USD",
            flat_fee=Decimal("0"),
            pct_fee=Decimal("0"),
        )

        amount = Decimal("0.01")

        buy_leg = calc_buy_leg(
            venue="kraken",
            pair="BTC/USD",
            price=Decimal("69113.0"),
            amount=amount,
            fee_pct=Decimal("0.0026"),
            withdrawal=kraken_w,
        )
        sell_leg = calc_sell_leg(
            venue="coinbase",
            pair="BTC/USD",
            price=Decimal("69200.0"),
            amount=amount,
            fee_pct=Decimal("0.006"),
            withdrawal=coinbase_w,
        )

        assert buy_leg.base_curr_amt == Decimal("691.130")
        assert buy_leg.trading_fee_base == Decimal("691.130") * Decimal("0.0026")

        assert sell_leg.base_curr_amt == Decimal("692.000")
        assert sell_leg.trading_fee_base == Decimal("692.000") * Decimal("0.006")

        buy_eff = effective_buy_cost(buy_leg)
        sell_eff = effective_sell_proceeds(sell_leg)
        assert buy_eff == Decimal("691.130") * Decimal("1.0026")
        assert sell_eff == Decimal("692.000") * Decimal("0.994")

        buy_total = total_buy_cost(buy_leg)
        sell_net = net_sell_proceeds(sell_leg)

        assert buy_total == buy_eff + Decimal("0.00005") * Decimal("69113.0")
        assert sell_net == sell_eff
