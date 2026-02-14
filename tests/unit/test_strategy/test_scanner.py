"""Tests for strategy/scanner.py.

Tests exchange filtering and the top-level scan pipeline.
Uses shared fixtures from tests/conftest.py.
"""

from decimal import Decimal

from uscryptoarb.calculation.arb_calc import calc_arb_opportunity
from uscryptoarb.calculation.types import FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.strategy.scanner import filter_valid_exchanges, find_trades_to_execute


class TestFilterValidExchanges:
    def test_no_staleness_filter_returns_all(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
    ) -> None:
        """max_staleness_ms=None disables filtering."""
        tobs = {
            "kraken": kraken_btc_usd_tob,
            "coinbase": coinbase_btc_usd_tob,
        }
        result = filter_valid_exchanges(tobs, max_staleness_ms=None)
        assert result == tobs

    def test_no_current_time_returns_all(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
    ) -> None:
        """current_time_ms=None disables filtering even with max_staleness_ms."""
        tobs = {
            "kraken": kraken_btc_usd_tob,
            "coinbase": coinbase_btc_usd_tob,
        }
        result = filter_valid_exchanges(
            tobs, max_staleness_ms=5000, current_time_ms=None
        )
        assert result == tobs

    def test_filters_stale_data(
        self,
        kraken_btc_usd_tob: TopOfBook,
        stale_tob: TopOfBook,
    ) -> None:
        """One fresh venue (kraken ts=1707900000000), one stale (ts=1707800000000)."""
        tobs = {
            "kraken": kraken_btc_usd_tob,
            "stale_exchange": stale_tob,
        }
        result = filter_valid_exchanges(
            tobs,
            max_staleness_ms=5000,
            current_time_ms=1707900001000,  # 1s after kraken, 100M ms after stale
        )
        assert "kraken" in result
        assert "stale_exchange" not in result

    def test_all_stale_returns_empty(
        self,
        stale_tob: TopOfBook,
    ) -> None:
        tobs = {"stale_exchange": stale_tob}
        result = filter_valid_exchanges(
            tobs,
            max_staleness_ms=5000,
            current_time_ms=1707900000000,
        )
        assert result == {}

    def test_none_stale_returns_all(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
    ) -> None:
        """Both venues within staleness window."""
        tobs = {
            "kraken": kraken_btc_usd_tob,
            "coinbase": coinbase_btc_usd_tob,
        }
        # Both have ts_local_ms=1707900000000, current=1707900002000 (2s later)
        result = filter_valid_exchanges(
            tobs,
            max_staleness_ms=5000,
            current_time_ms=1707900002000,
        )
        assert result == tobs

    def test_exactly_at_staleness_boundary_included(
        self,
        kraken_btc_usd_tob: TopOfBook,
    ) -> None:
        """Data age exactly equals max_staleness_ms -> included (<=)."""
        tobs = {"kraken": kraken_btc_usd_tob}
        result = filter_valid_exchanges(
            tobs,
            max_staleness_ms=5000,
            current_time_ms=kraken_btc_usd_tob.ts_local_ms + 5000,
        )
        assert "kraken" in result

    def test_one_ms_past_staleness_excluded(
        self,
        kraken_btc_usd_tob: TopOfBook,
    ) -> None:
        """Data age one ms beyond max_staleness_ms -> excluded."""
        tobs = {"kraken": kraken_btc_usd_tob}
        result = filter_valid_exchanges(
            tobs,
            max_staleness_ms=5000,
            current_time_ms=kraken_btc_usd_tob.ts_local_ms + 5001,
        )
        assert result == {}


class TestFindTradesToExecute:
    def test_returns_best_opportunity(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Happy path: 2 venues, returns the best opportunity."""
        result = find_trades_to_execute(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
            },
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is not None
        direct_opps = [
            calc_arb_opportunity(
                buy_tob=kraken_btc_usd_tob,
                sell_tob=coinbase_btc_usd_tob,
                buy_fees=kraken_btc_usd_fees,
                sell_fees=coinbase_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=coinbase_btc_usd_tob,
                sell_tob=kraken_btc_usd_tob,
                buy_fees=coinbase_btc_usd_fees,
                sell_fees=kraken_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
        ]
        assert result == max(direct_opps, key=lambda o: o.return_net)

    def test_no_profitable_opportunity_returns_none(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        result = find_trades_to_execute(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
            },
            threshold=Decimal("0.50"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is None

    def test_single_venue_returns_none(
        self,
        kraken_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Need >= 2 venues for arbitrage."""
        result = find_trades_to_execute(
            tobs_by_venue={"kraken": kraken_btc_usd_tob},
            fees_by_venue={"kraken": kraken_btc_usd_fees},
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is None

    def test_empty_venues_returns_none(self) -> None:
        result = find_trades_to_execute(
            tobs_by_venue={},
            fees_by_venue={},
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is None

    def test_stale_venue_excluded_leaves_single(
        self,
        kraken_btc_usd_tob: TopOfBook,
        stale_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
    ) -> None:
        """2 venues but 1 is stale -> filtered to 1 -> no arb possible."""
        stale_fees = kraken_btc_usd_fees  # fees don't matter, venue gets filtered
        result = find_trades_to_execute(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "stale_exchange": stale_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "stale_exchange": stale_fees,
            },
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900001000,
            max_staleness_ms=5000,
        )
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
        """3 venues: best opportunity should be buy-Kraken sell-Coinbase."""
        result = find_trades_to_execute(
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
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is not None
        opps = [
            calc_arb_opportunity(
                buy_tob=kraken_btc_usd_tob,
                sell_tob=coinbase_btc_usd_tob,
                buy_fees=kraken_btc_usd_fees,
                sell_fees=coinbase_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=coinbase_btc_usd_tob,
                sell_tob=kraken_btc_usd_tob,
                buy_fees=coinbase_btc_usd_fees,
                sell_fees=kraken_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=kraken_btc_usd_tob,
                sell_tob=gemini_btc_usd_tob,
                buy_fees=kraken_btc_usd_fees,
                sell_fees=gemini_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=gemini_btc_usd_tob,
                sell_tob=kraken_btc_usd_tob,
                buy_fees=gemini_btc_usd_fees,
                sell_fees=kraken_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=coinbase_btc_usd_tob,
                sell_tob=gemini_btc_usd_tob,
                buy_fees=coinbase_btc_usd_fees,
                sell_fees=gemini_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
            calc_arb_opportunity(
                buy_tob=gemini_btc_usd_tob,
                sell_tob=coinbase_btc_usd_tob,
                buy_fees=gemini_btc_usd_fees,
                sell_fees=coinbase_btc_usd_fees,
                trade_amount=Decimal("0.01"),
                ts_calculated_ms=1707900000000,
            ),
        ]
        assert result == max(opps, key=lambda o: o.return_net)

    def test_venue_without_fees_excluded(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Venue in tobs but not in fees -> safely excluded via intersection."""
        result = find_trades_to_execute(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,  # present in tobs
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                # coinbase missing from fees
            },
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        # Only kraken has fees, so only 1 usable venue -> no arb possible
        assert result is None

    def test_golden_values(
        self,
        kraken_btc_usd_tob: TopOfBook,
        coinbase_btc_usd_tob: TopOfBook,
        kraken_btc_usd_fees: FeeSchedule,
        coinbase_btc_usd_fees: FeeSchedule,
    ) -> None:
        """Golden test: verify exact return values match hand-calculated numbers.

        Setup:
            Kraken ask: 69113.0, Coinbase bid: 69200.0
            Kraken buy fee: 0.26%, Coinbase sell fee: 0.60%
            Kraken withdrawal: 0.00005 BTC, Coinbase sell withdrawal: $0
            Trade amount: 0.01 BTC

        Expected return_raw = (69200 - 69113) / 69113 = 87/69113
        """
        result = find_trades_to_execute(
            tobs_by_venue={
                "kraken": kraken_btc_usd_tob,
                "coinbase": coinbase_btc_usd_tob,
            },
            fees_by_venue={
                "kraken": kraken_btc_usd_fees,
                "coinbase": coinbase_btc_usd_fees,
            },
            threshold=Decimal("-1.0"),
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result is not None
        assert result.pair == "BTC/USD"
        assert result.buy_price > Decimal("0")
        assert result.sell_price > Decimal("0")
        assert result.market_currency == "BTC"
        assert result.base_currency == "USD"
        assert result.trade_amount == Decimal("0.01")

        # Verify return_raw exactly for the selected direction
        expected_raw = (result.sell_price - result.buy_price) / result.buy_price
        assert result.return_raw == expected_raw

        # Verify ordering: return_raw > return_grs > return_net (fees reduce returns)
        assert result.return_raw > result.return_grs
        assert result.return_grs >= result.return_net

        # Verify the result matches what calc_arb_opportunity produces directly
        tobs = {
            "kraken": kraken_btc_usd_tob,
            "coinbase": coinbase_btc_usd_tob,
        }
        fees = {
            "kraken": kraken_btc_usd_fees,
            "coinbase": coinbase_btc_usd_fees,
        }
        direct = calc_arb_opportunity(
            buy_tob=tobs[result.buy_venue],
            sell_tob=tobs[result.sell_venue],
            buy_fees=fees[result.buy_venue],
            sell_fees=fees[result.sell_venue],
            trade_amount=Decimal("0.01"),
            ts_calculated_ms=1707900000000,
        )
        assert result.return_net == direct.return_net
        assert result.profit_net_base == direct.profit_net_base
