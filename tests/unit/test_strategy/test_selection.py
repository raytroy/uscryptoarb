"""Tests for strategy/selection.py.

Tests trade selection logic: threshold checks and best-trade picking.
Uses shared fixtures from tests/conftest.py.
"""

from decimal import Decimal

from uscryptoarb.calculation.arb_calc import calc_all_opportunities, calc_arb_opportunity
from uscryptoarb.calculation.types import FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.strategy.selection import passes_threshold, select_trade


class TestPassesThreshold:
    def test_above_threshold_returns_true(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # return_raw is positive (buy Kraken ask 69113, sell Coinbase bid 69200)
        # Use a very low threshold that any positive spread should pass
        assert passes_threshold(opp, Decimal("-1.0"))

    def test_below_threshold_returns_false(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Threshold higher than any realistic return
        assert not passes_threshold(opp, Decimal("0.50"))

    def test_exactly_at_threshold_returns_false(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Boundary test: exactly at threshold is REJECTED (strictly greater)."""
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Set threshold to exactly the return_net value
        assert not passes_threshold(opp, opp.return_net)

    def test_just_above_threshold_returns_true(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Boundary test: just below the value passes (value > threshold)."""
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Threshold slightly below return_net
        threshold = opp.return_net - Decimal("0.0001")
        assert passes_threshold(opp, threshold)

    def test_custom_metric_return_raw(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # return_raw > return_net, so a threshold between them
        # should pass for return_raw but fail for return_net
        between = (opp.return_raw + opp.return_net) / 2
        assert passes_threshold(opp, between, metric="return_raw")
        assert not passes_threshold(opp, between, metric="return_net")


class TestSelectTrade:
    def test_returns_best_opportunity(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opps = calc_all_opportunities(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
            },
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Very low threshold — both directions might qualify, best should win
        best = select_trade(opps, Decimal("-1.0"))
        assert best is not None
        expected = max(opps, key=lambda o: o.return_net)
        assert best == expected

    def test_no_qualifying_trades_returns_none(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opps = calc_all_opportunities(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
            },
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Impossibly high threshold
        result = select_trade(opps, Decimal("0.50"))
        assert result is None

    def test_empty_list_returns_none(self) -> None:
        result = select_trade([], Decimal("0.001"))
        assert result is None

    def test_single_opportunity_above_threshold(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        result = select_trade([opp], Decimal("-1.0"))
        assert result is opp

    def test_single_opportunity_below_threshold_returns_none(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=kraken_btc_usd_tob,
            sell_tob=coinbase_btc_usd_tob,
            buy_fees=kraken_btc_usd_fees,
            sell_fees=coinbase_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        result = select_trade([opp], Decimal("0.50"))
        assert result is None

    def test_three_venues_returns_best(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        gemini_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
        gemini_btc_usd_fees: FeeSchedule,
    ) -> None:
        """3 venues = 6 directional opportunities. Best should be returned."""
        opps = calc_all_opportunities(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
                "gemini": gemini_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
                "gemini": gemini_btc_usd_fees,
            },
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert len(opps) == 6  # 3 * 2 = 6 permutations
        best = select_trade(opps, Decimal("-1.0"))
        assert best is not None
        expected = max(opps, key=lambda o: o.return_net)
        assert best == expected
