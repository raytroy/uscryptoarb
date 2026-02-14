"""Tests for calculation/arb_calc.py.

End-to-end tests using fixtures from conftest.py.
Verifies the complete flow: TopOfBook + FeeSchedule → ArbOpportunity.
"""

from decimal import Decimal

import pytest

from uscryptoarb.calculation.arb_calc import (
    calc_all_opportunities,
    calc_arb_opportunity,
    filter_profitable,
    sort_opportunities,
)
from uscryptoarb.calculation.types import FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook


class TestCalcArbOpportunity:
    def test_buy_kraken_sell_coinbase(
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

        assert opp.pair == "BTC/USD"
        assert opp.buy_venue == "kraken"
        assert opp.sell_venue == "coinbase"
        assert opp.buy_price == Decimal("69113.0")
        assert opp.sell_price == Decimal("69200.0")
        assert opp.market_currency == "BTC"
        assert opp.base_currency == "USD"
        assert opp.trade_amount == Decimal("0.01")

        assert opp.return_raw > Decimal("0")
        expected_raw = Decimal("87") / Decimal("69113")
        assert opp.return_raw == expected_raw
        assert opp.return_grs < opp.return_raw
        assert opp.return_net <= opp.return_grs

    def test_buy_coinbase_sell_kraken_negative(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        opp = calc_arb_opportunity(
            buy_tob=coinbase_btc_usd_tob,
            sell_tob=kraken_btc_usd_tob,
            buy_fees=coinbase_btc_usd_fees,
            sell_fees=kraken_btc_usd_fees,
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )

        assert opp.buy_venue == "coinbase"
        assert opp.sell_venue == "kraken"
        assert opp.return_raw < Decimal("0")
        assert opp.profit_net_base < Decimal("0")

    def test_leg_details_populated(
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

        assert opp.buy_leg.venue == "kraken"
        assert opp.buy_leg.side == "buy"
        assert opp.buy_leg.fee_rate == Decimal("0.0026")

        assert opp.sell_leg.venue == "coinbase"
        assert opp.sell_leg.side == "sell"
        assert opp.sell_leg.fee_rate == Decimal("0.006")

    def test_frozen_output(
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
        with pytest.raises(AttributeError):
            opp.return_net = Decimal("999")  # type: ignore[misc]


class TestCalcAllOpportunities:
    def test_two_venues_generates_two_opps(
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
        assert len(opps) == 2

        venues = {(o.buy_venue, o.sell_venue) for o in opps}
        assert ("kraken", "coinbase") in venues
        assert ("coinbase", "kraken") in venues

    def test_single_venue_returns_empty(
        self,
        kraken_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
    ) -> None:
        opps = calc_all_opportunities(
            tobs_by_venue={"kraken": kraken_btc_usd_tob},
            fees_by_venue={"kraken": kraken_btc_usd_fees},
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert opps == []

    def test_empty_venues_returns_empty(self) -> None:
        opps = calc_all_opportunities(
            tobs_by_venue={},
            fees_by_venue={},
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert opps == []


class TestSortOpportunities:
    def test_sort_by_return_net_descending(
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

        sorted_opps = sort_opportunities(opps, by="return_net")
        assert sorted_opps[0].return_net >= sorted_opps[1].return_net

    def test_sort_does_not_mutate(
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
        original_order = [o.buy_venue for o in opps]
        sort_opportunities(opps, by="return_raw")
        assert [o.buy_venue for o in opps] == original_order


class TestFilterProfitable:
    def test_filters_below_threshold(
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

        filtered = filter_profitable(opps, threshold=Decimal("0.10"))
        assert len(filtered) == 0

        filtered = filter_profitable(opps, threshold=Decimal("-1.0"))
        assert len(filtered) == len(opps)
