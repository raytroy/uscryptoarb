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
from enum import Enum, auto

from uscryptoarb.calculation.arb_calc import calc_all_opportunities
from uscryptoarb.calculation.calc_types import ArbOpportunity, FeeSchedule
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.strategy.selection import select_trade


class RejectionReason(Enum):
    """Structured reason why find_trades_to_execute returned no opportunity.

    Provides diagnostic telemetry for operators to distinguish between
    different "no trade" scenarios without parsing log messages.
    """

    INSUFFICIENT_VENUES = auto()
    ALL_STALE = auto()
    MISSING_FEES = auto()
    BELOW_THRESHOLD = auto()


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
) -> ArbOpportunity | RejectionReason:
    """Top-level pipeline: filter -> calc_all -> select.

    This is the Mathematica TradesToExecute[] equivalent.
    Composes existing calculation layer functions into a single
    detection pipeline.

    Returns:
        The best ArbOpportunity above threshold, or a RejectionReason
        explaining why no trade was found.
    """
    original_count = len(tobs_by_venue)

    # Step 1: Filter stale exchanges
    fresh_tobs = filter_valid_exchanges(
        tobs_by_venue,
        max_staleness_ms=max_staleness_ms,
        current_time_ms=ts_calculated_ms,
    )

    if len(fresh_tobs) < 2:
        if original_count < 2:
            return RejectionReason.INSUFFICIENT_VENUES
        return RejectionReason.ALL_STALE

    # Step 2: Intersect with venues that have fee data.
    usable_venues = set(fresh_tobs) & set(fees_by_venue)
    if len(usable_venues) < 2:
        return RejectionReason.MISSING_FEES

    usable_tobs = {v: fresh_tobs[v] for v in usable_venues}
    usable_fees = {v: fees_by_venue[v] for v in usable_venues}

    # Step 3: Calculate all pairwise opportunities
    opportunities = calc_all_opportunities(
        tobs_by_venue=usable_tobs,
        fees_by_venue=usable_fees,
        trade_amount=trade_amount,
        ts_calculated_ms=ts_calculated_ms,
    )

    # Step 4: Select best above threshold
    best = select_trade(opportunities, threshold)
    if best is None:
        return RejectionReason.BELOW_THRESHOLD

    return best
