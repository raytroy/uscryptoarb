"""
Trade selection — threshold checks and best-trade picking.

Pure functions that decide whether an arbitrage opportunity is worth
executing and which single opportunity is the best candidate.

NO I/O. NO validation. NO side effects. (DEC-002, DEC-003, LL-020)
All monetary values use Decimal (DEC-007, LL-010).

Mathematica equivalents:
    SelectTradeToExecute[] -> select_trade()

Intentional improvements over Mathematica (DEC-012):
    - Mathematica checks returnRaw >= threshold AND returnGrs >= threshold.
      Python checks only return_net > threshold. Since
      return_net <= return_grs <= return_raw (fees only reduce returns),
      passing return_net automatically implies the others pass. This is
      both simpler and MORE conservative.
    - Mathematica uses >= (greater-or-equal). Python uses > (strictly
      greater-than). An opportunity exactly at threshold could easily
      slip below due to timing or slippage. Conservative by design.
    - Mathematica sorts by smallest sellMarket amount (execution sizing).
      Python sorts by highest return_net (appropriate for Phase 1
      detection without sizing data). Phase 4 can add sizing-based
      selection when balance data is available.
"""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from uscryptoarb.calculation.arb_calc import sort_opportunities
from uscryptoarb.calculation.types import ArbOpportunity


def passes_threshold(
    opportunity: ArbOpportunity,
    threshold: Decimal,
    metric: str = "return_net",
) -> bool:
    """Check if an opportunity exceeds the minimum return threshold.

    Uses strictly-greater-than (not >=) for conservative filtering.
    An opportunity exactly at threshold is rejected — it could easily
    slip below due to timing or slippage.

    Related to calculation.arb_calc.filter_profitable(), which applies
    the same > logic across a list. This function is a single-item
    convenience for readability in select_trade().

    Args:
        opportunity: The arb opportunity to evaluate.
        threshold: Minimum return value (e.g. Decimal("0.0055")).
        metric: Which return metric to check. Default "return_net".

    Returns:
        True if the opportunity's metric exceeds the threshold.
    """
    value = cast(Decimal, getattr(opportunity, metric))
    return value > threshold


def select_trade(
    opportunities: list[ArbOpportunity],
    threshold: Decimal,
) -> ArbOpportunity | None:
    """Pick the single best trade from a list of opportunities.

    Filters opportunities that exceed the threshold on return_net,
    sorts by return_net descending, and returns the best one.

    Mathematica equivalent: SelectTradeToExecute[].
    See module docstring for intentional differences.

    Args:
        opportunities: List of ArbOpportunity to evaluate.
            May be empty. Assumed already computed by calc_all_opportunities.
        threshold: Minimum return_net to qualify (e.g. Decimal("0.0055")).

    Returns:
        The best ArbOpportunity above threshold, or None if none qualify.
    """
    qualifying = [o for o in opportunities if passes_threshold(o, threshold)]
    if not qualifying:
        return None
    ranked = sort_opportunities(qualifying, by="return_net", descending=True)
    return ranked[0]
