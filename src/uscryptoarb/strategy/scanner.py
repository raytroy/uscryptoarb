"""
Arbitrage scanner — top-level pipeline for trade detection.

Composes calculation layer functions into a single pipeline:
    filter exchanges -> calculate all opportunities -> sort -> select best.

This is the Python equivalent of Mathematica's TradesToExecute[].

NO I/O. NO validation. NO side effects. (DEC-002, DEC-003, LL-020)
All monetary values use Decimal (DEC-007, LL-010).

Mathematica equivalents:
    TradesToExecute[]      -> find_trades_to_execute()
    TrimExchangesToCalc[]  -> filter_valid_exchanges()

Intentional improvements over Mathematica (DEC-012):
    - TrimExchangesToCalc had L1/L2/L3 variants for different filtering
      criteria. Python combines them into a single function with optional
      staleness parameter.
    - NonDupExchangesWithMoney[] (balance-based filtering) is deferred
      to Phase 3+ when authenticated balance queries are available.
"""

from __future__ import annotations

from decimal import Decimal

from uscryptoarb.calculation.arb_calc import calc_all_opportunities, sort_opportunities
from uscryptoarb.calculation.types import ArbOpportunity, FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.strategy.selection import select_trade


def filter_valid_exchanges(
    tobs_by_venue: dict[str, TopOfBook],
    max_staleness_ms: int | None = None,
    current_time_ms: int | None = None,
) -> dict[str, TopOfBook]:
    """Filter to exchanges with valid, non-stale market data.

    This is strategic filtering ("is this data fresh enough to trade on?"),
    not boundary validation. The TopOfBook objects are already validated;
    this function decides whether they are recent enough to use.

    Mathematica equivalent: TrimExchangesToCalc[] (combined L1/L2/L3).

    Staleness filtering is skipped (all venues returned) when:
    - max_staleness_ms is None (staleness checking disabled), OR
    - current_time_ms is None (no reference time provided).
    This is the safest default — never accidentally blocks a venue.

    Args:
        tobs_by_venue: {venue_name: TopOfBook} for a single pair.
        max_staleness_ms: Maximum age in milliseconds. None disables filtering.
        current_time_ms: Reference "now" timestamp in ms. Must be provided
            by the caller (orchestration layer) to keep this function pure.
            None disables filtering.

    Returns:
        Filtered dict containing only venues with fresh-enough data.
        Returns input unchanged if staleness filtering is disabled.
    """
    if max_staleness_ms is None or current_time_ms is None:
        return tobs_by_venue

    return {
        venue: tob
        for venue, tob in tobs_by_venue.items()
        if (current_time_ms - tob.ts_local_ms) <= max_staleness_ms
    }


def find_trades_to_execute(
    *,
    tobs_by_venue: dict[str, TopOfBook],
    fees_by_venue: dict[str, FeeSchedule],
    threshold: Decimal,
    trade_amount: Decimal,
    ts_calculated_ms: int,
    max_staleness_ms: int | None = None,
) -> ArbOpportunity | None:
    """Top-level pipeline: filter -> calc_all -> sort -> select.

    This is the Mathematica TradesToExecute[] equivalent.
    Composes existing calculation layer functions into a single
    detection pipeline.

    The pipeline:
        1. filter_valid_exchanges() — remove stale data
        2. Intersect with fees_by_venue keys — only venues we have fee data for
        3. calc_all_opportunities() — N*(N-1) directional opportunities
        4. sort_opportunities() — rank by return_net descending
        5. select_trade() — pick the best above threshold, or None

    Preconditions (enforced by orchestration, trusted here per DEC-003):
        - All TopOfBook objects are already validated (non-crossed, positive prices)
        - fees_by_venue contains entries for all configured venues
        - threshold and trade_amount are positive Decimals

    Args:
        tobs_by_venue: {venue_name: TopOfBook} for a single pair.
        fees_by_venue: {venue_name: FeeSchedule} for the same pair.
        threshold: Minimum return_net to qualify (e.g. Decimal("0.0055")).
        trade_amount: Reference amount in market currency for return calc.
        ts_calculated_ms: Timestamp of this scan cycle in ms since epoch.
            Also used as the reference time for staleness filtering.
        max_staleness_ms: Maximum data age in ms. None disables filtering.

    Returns:
        The best ArbOpportunity above threshold, or None if none qualify
        or fewer than 2 valid venues remain after filtering.
    """
    # Step 1: Filter stale exchanges
    fresh_tobs = filter_valid_exchanges(
        tobs_by_venue,
        max_staleness_ms=max_staleness_ms,
        current_time_ms=ts_calculated_ms,
    )

    # Step 2: Intersect with venues that have fee data.
    # This is a set operation (not validation) — ensures calc_all_opportunities
    # won't KeyError on a venue present in tobs but absent from fees.
    usable_venues = set(fresh_tobs.keys()) & set(fees_by_venue.keys())
    filtered_tobs = {v: fresh_tobs[v] for v in usable_venues}
    filtered_fees = {v: fees_by_venue[v] for v in usable_venues}

    # Step 3: Calculate all pairwise opportunities
    all_opps = calc_all_opportunities(
        tobs_by_venue=filtered_tobs,
        fees_by_venue=filtered_fees,
        trade_amount=trade_amount,
        ts_calculated_ms=ts_calculated_ms,
    )

    # Step 4: Sort opportunities by return_net descending
    ranked_opps = sort_opportunities(all_opps, by="return_net", descending=True)

    # Step 5: Select best above threshold
    return select_trade(ranked_opps, threshold)
