"""
Kelly Criterion position sizing for arbitrage trades.

Ports the Mathematica CalcKellyAmount[] function with improvements:
- Explicit edge-floor clamping (returns 0 if edge ≤ 0)
- Max-fraction cap to prevent oversized positions
- Exchange precision compliance via floor_to_step()

Mathematica source:
    Kelly[edge_, probability_] := edge / (1/probability)
    → simplifies to: edge * probability

    CalcKellyAmount[balance, tradeToInvestigate, probSuccess, kellyNumber, threshold] :=
        Kelly[returnGrs - threshold, probSuccess] * kellyNumber * balance

Industry-standard defaults (DEC-014):
    prob_success = 0.95  (95% historical success rate)
    kelly_multiplier = 0.25  (quarter Kelly — conservative)

All functions are pure. No validation (DEC-003).
All monetary values use Decimal (DEC-007, LL-010).
"""

from __future__ import annotations

from decimal import Decimal

from uscryptoarb.calculation.types import TradingAccuracy
from uscryptoarb.misc.decimals import floor_to_step

ZERO = Decimal("0")

# DEC-014: Industry-standard Kelly Criterion defaults
DEFAULT_PROB_SUCCESS = Decimal("0.95")
DEFAULT_KELLY_MULTIPLIER = Decimal("0.25")

# Safety cap: never risk more than this fraction of bankroll on one trade,
# regardless of what Kelly says. Separate from config min_bankroll_limit.
MAX_KELLY_FRACTION = Decimal("0.10")


def calc_kelly_fraction(edge: Decimal, prob_success: Decimal) -> Decimal:
    """Pure Kelly fraction: how much of bankroll to risk.

    Kelly[edge, probability] = edge × probability

    This is the theoretical optimal fraction. In practice, we scale
    it down with kelly_multiplier (fractional Kelly) for safety.

    Args:
        edge: Return above threshold (returnGrs - threshold).
               Must be > 0 for a positive Kelly fraction.
        prob_success: Probability of successful execution (0..1).

    Returns:
        Kelly fraction (0 if edge ≤ 0).
    """
    if edge <= ZERO:
        return ZERO
    return edge * prob_success


def calc_kelly_amount(
    *,
    bankroll: Decimal,
    return_grs: Decimal,
    threshold: Decimal,
    prob_success: Decimal = DEFAULT_PROB_SUCCESS,
    kelly_multiplier: Decimal = DEFAULT_KELLY_MULTIPLIER,
    max_fraction: Decimal = MAX_KELLY_FRACTION,
) -> Decimal:
    """Calculate position size in base currency using fractional Kelly.

    Mathematica: Kelly[returnGrs - threshold, probSuccess] × kellyNumber × balance

    Safety features beyond Mathematica:
    - Returns 0 if edge ≤ 0 (no bet when return doesn't exceed threshold)
    - Caps at max_fraction × bankroll (prevents oversized positions)

    Args:
        bankroll: Total available balance in base currency (e.g. $1000).
        return_grs: Gross return of the opportunity (after trading fees).
        threshold: Minimum acceptable return from config (e.g. 0.0055).
        prob_success: Probability of successful execution (default 0.95).
        kelly_multiplier: Fractional Kelly scaling (default 0.25 = quarter Kelly).
        max_fraction: Maximum fraction of bankroll per trade (default 0.10).

    Returns:
        Position size in base currency (Decimal ≥ 0).

    Example:
        bankroll=$1000, returnGrs=0.008, threshold=0.0055,
        prob=0.95, kelly=0.25:
        edge = 0.008 - 0.0055 = 0.0025
        kelly_frac = 0.0025 × 0.95 = 0.002375
        raw_amount = 0.002375 × 0.25 × 1000 = $0.59
    """
    edge = return_grs - threshold
    kelly_frac = calc_kelly_fraction(edge, prob_success)

    raw_amount = kelly_frac * kelly_multiplier * bankroll

    # Cap at max_fraction of bankroll
    cap = max_fraction * bankroll
    if raw_amount > cap:
        raw_amount = cap

    return raw_amount


def calc_position_size(
    *,
    kelly_amount_base: Decimal,
    price: Decimal,
    accuracy: TradingAccuracy,
) -> Decimal:
    """Convert base currency amount to exchange-compliant market currency order size.

    Takes the Kelly amount (in base currency, e.g. USD) and converts
    to market currency (e.g. BTC), then floors to exchange lot_step
    and enforces min/max order size.

    Args:
        kelly_amount_base: Position size in base currency from calc_kelly_amount().
        price: Current price (used to convert base → market currency).
        accuracy: Exchange precision constraints.

    Returns:
        Order size in market currency, compliant with exchange rules.
        Returns 0 if the calculated size is below min_order_size.
    """
    # Convert base currency → market currency
    raw_size = kelly_amount_base / price

    # Floor to exchange lot step
    floored = floor_to_step(raw_size, accuracy.lot_step)

    # Enforce minimum
    if floored < accuracy.min_order_size:
        return ZERO

    # Enforce maximum (if set)
    if accuracy.max_order_size is not None and floored > accuracy.max_order_size:
        floored = floor_to_step(accuracy.max_order_size, accuracy.lot_step)

    return floored
