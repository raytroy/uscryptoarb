"""
Arbitrage opportunity calculator — the heart of the calculation layer.

Takes pairs of TopOfBook snapshots from different exchanges and evaluates
the full arb opportunity: raw return, gross return (after trading fees),
net return (after all fees), and absolute profit.

For Type-2 arbitrage (same pair, different exchanges):
    Buy on the exchange with the lower ask → sell on the exchange with the higher bid.

All functions are pure. No I/O, no validation (DEC-003, LL-020).
All monetary values use Decimal (DEC-007, LL-010).

Mathematica equivalents:
    ArbCalcFinal[]  → calc_arb_opportunity
    ArbOppAll[]     → calc_all_opportunities
    ArbReturns[]    → sort_opportunities
"""

from __future__ import annotations

import itertools
from decimal import Decimal

from uscryptoarb.calculation.fees import (
    calc_buy_leg,
    calc_sell_leg,
    effective_buy_cost,
    effective_sell_proceeds,
    net_sell_proceeds,
    total_buy_cost,
)
from uscryptoarb.calculation.returns import (
    calc_profit_base,
    calc_return_grs,
    calc_return_net,
    calc_return_raw,
)
from uscryptoarb.calculation.types import ArbOpportunity, FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.markets.pairs import parse_pair

ZERO = Decimal("0")


def calc_arb_opportunity(
    *,
    buy_tob: TopOfBook,
    sell_tob: TopOfBook,
    buy_fees: FeeSchedule,
    sell_fees: FeeSchedule,
    trade_amount: Decimal,
    ts_calculated_ms: int,
) -> ArbOpportunity:
    """Evaluate a single Type-2 arbitrage opportunity.

    Buy market currency on buy_tob's exchange (at the ask),
    sell on sell_tob's exchange (at the bid).

    The trade_amount is in market currency units (e.g. 0.1 BTC).
    In Phase 1 detection, this is a reference amount for return
    calculation — actual sizing uses Kelly Criterion separately.

    Args:
        buy_tob: TopOfBook from the exchange where we BUY (lower ask).
        sell_tob: TopOfBook from the exchange where we SELL (higher bid).
        buy_fees: Fee schedule for the buy exchange.
        sell_fees: Fee schedule for the sell exchange.
        trade_amount: Market currency amount to evaluate (e.g. Decimal("0.01")).
        ts_calculated_ms: Timestamp of this calculation in ms since epoch.

    Returns:
        ArbOpportunity with full breakdown.
    """
    buy_price = buy_tob.ask_px  # we buy at the ask
    sell_price = sell_tob.bid_px  # we sell at the bid

    # Parse pair for currency labels
    cp = parse_pair(buy_tob.pair)

    # Calculate both legs with fee breakdowns
    buy_leg = calc_buy_leg(
        venue=buy_tob.venue,
        pair=buy_tob.pair,
        price=buy_price,
        amount=trade_amount,
        fee_pct=buy_fees.buy_fee.pct_fee,
        flat_fee=buy_fees.buy_fee.flat_fee,
        withdrawal=buy_fees.buy_withdrawal,
    )

    sell_leg = calc_sell_leg(
        venue=sell_tob.venue,
        pair=sell_tob.pair,
        price=sell_price,
        amount=trade_amount,
        fee_pct=sell_fees.sell_fee.pct_fee,
        flat_fee=sell_fees.sell_fee.flat_fee,
        withdrawal=sell_fees.sell_withdrawal,
    )

    # Return calculations at three levels
    return_raw = calc_return_raw(buy_price, sell_price)

    buy_cost_grs = effective_buy_cost(buy_leg)
    sell_proceeds_grs = effective_sell_proceeds(sell_leg)
    return_grs = calc_return_grs(buy_cost_grs, sell_proceeds_grs)
    profit_grs = calc_profit_base(buy_cost_grs, sell_proceeds_grs)

    buy_cost_net = total_buy_cost(buy_leg)
    sell_proceeds_net = net_sell_proceeds(sell_leg)
    return_net = calc_return_net(buy_cost_net, sell_proceeds_net)
    profit_net = calc_profit_base(buy_cost_net, sell_proceeds_net)

    return ArbOpportunity(
        pair=buy_tob.pair,
        buy_venue=buy_tob.venue,
        sell_venue=sell_tob.venue,
        buy_price=buy_price,
        sell_price=sell_price,
        return_raw=return_raw,
        return_grs=return_grs,
        return_net=return_net,
        profit_grs_base=profit_grs,
        profit_net_base=profit_net,
        buy_leg=buy_leg,
        sell_leg=sell_leg,
        market_currency=cp.base,
        base_currency=cp.quote,
        trade_amount=trade_amount,
        ts_calculated_ms=ts_calculated_ms,
    )


def calc_all_opportunities(
    *,
    tobs_by_venue: dict[str, TopOfBook],
    fees_by_venue: dict[str, FeeSchedule],
    trade_amount: Decimal,
    ts_calculated_ms: int,
) -> list[ArbOpportunity]:
    """Generate all pairwise arb opportunities for a single trading pair.

    For N venues, this produces N×(N-1) directional opportunities
    (each pair considered in both buy/sell directions).

    Args:
        tobs_by_venue: {venue_name: TopOfBook} for the same pair.
        fees_by_venue: {venue_name: FeeSchedule} for the same pair.
        trade_amount: Reference amount in market currency.
        ts_calculated_ms: Timestamp of this calculation.

    Returns:
        List of ArbOpportunity for all pairwise combinations.
        Empty list if fewer than 2 venues have data.
    """
    venues = list(tobs_by_venue.keys())
    if len(venues) < 2:
        return []

    opportunities: list[ArbOpportunity] = []

    for buy_venue, sell_venue in itertools.permutations(venues, 2):
        buy_tob = tobs_by_venue[buy_venue]
        sell_tob = tobs_by_venue[sell_venue]
        buy_fee = fees_by_venue[buy_venue]
        sell_fee = fees_by_venue[sell_venue]

        opp = calc_arb_opportunity(
            buy_tob=buy_tob,
            sell_tob=sell_tob,
            buy_fees=buy_fee,
            sell_fees=sell_fee,
            trade_amount=trade_amount,
            ts_calculated_ms=ts_calculated_ms,
        )
        opportunities.append(opp)

    return opportunities


def sort_opportunities(
    opps: list[ArbOpportunity],
    *,
    by: str = "return_net",
    descending: bool = True,
) -> list[ArbOpportunity]:
    """Sort arbitrage opportunities by a return metric.

    Mathematica equivalent: ArbReturns[] / ArbSort[].

    Args:
        opps: List of opportunities to sort.
        by: Attribute name to sort by. One of:
            "return_raw", "return_grs", "return_net",
            "profit_grs_base", "profit_net_base".
        descending: If True, highest return first (default).

    Returns:
        New sorted list (does not mutate input).
    """
    return sorted(
        opps,
        key=lambda o: getattr(o, by),
        reverse=descending,
    )


def filter_profitable(
    opps: list[ArbOpportunity],
    *,
    threshold: Decimal = ZERO,
    metric: str = "return_net",
) -> list[ArbOpportunity]:
    """Filter opportunities that exceed a minimum return threshold.

    Args:
        opps: List of opportunities to filter.
        threshold: Minimum return value (e.g. Decimal("0.0055")).
        metric: Which return metric to check against threshold.

    Returns:
        New filtered list containing only opportunities above threshold.
    """
    return [o for o in opps if getattr(o, metric) > threshold]
