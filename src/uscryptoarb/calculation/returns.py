"""
Return calculation functions for arbitrage analysis.

All functions are pure: same inputs → same outputs, no side effects.
All monetary values use Decimal (DEC-007). No validation — inputs
are already-validated domain types (DEC-003, LL-020).

Mathematica equivalents:
    ReturnCalc[]  → calc_return_raw, calc_return_grs, calc_return_net
    ReturnCalcAll[] uses these internally
"""

from __future__ import annotations

from decimal import Decimal


def calc_return_raw(buy_price: Decimal, sell_price: Decimal) -> Decimal:
    """Raw return before any fees.

    Formula: (sell_price - buy_price) / buy_price

    A positive return means selling is more expensive than buying,
    which is the precondition for profitable arbitrage.

    Args:
        buy_price: Best ask on the buy exchange (what you pay).
        sell_price: Best bid on the sell exchange (what you receive).

    Returns:
        Decimal return as a fraction (e.g. 0.008 = 0.8%).
    """
    return (sell_price - buy_price) / buy_price


def calc_return_grs(
    buy_cost_base: Decimal,
    sell_proceeds_base: Decimal,
) -> Decimal:
    """Gross return after trading fees (before withdrawal fees).

    Formula: (sell_proceeds - buy_cost) / buy_cost

    buy_cost_base includes the buy-side trading fee (cost perspective).
    sell_proceeds_base has the sell-side trading fee deducted.

    Args:
        buy_cost_base: Total cost in base currency including buy fee.
        sell_proceeds_base: Net proceeds in base currency after sell fee.

    Returns:
        Decimal return as a fraction.
    """
    return (sell_proceeds_base - buy_cost_base) / buy_cost_base


def calc_return_net(
    buy_total_cost: Decimal,
    sell_net_proceeds: Decimal,
) -> Decimal:
    """Net return after ALL fees (trading + withdrawal).

    Formula: (sell_net - buy_total) / buy_total

    This is the true profitability metric. A trade is only worth
    executing if return_net > threshold (from config).

    Args:
        buy_total_cost: Total cost including buy trading fee + any withdrawal fee.
        sell_net_proceeds: Net proceeds after sell trading fee + withdrawal fee.

    Returns:
        Decimal return as a fraction.
    """
    return (sell_net_proceeds - buy_total_cost) / buy_total_cost


def calc_profit_base(cost_base: Decimal, proceeds_base: Decimal) -> Decimal:
    """Absolute profit in base currency.

    Simple subtraction: proceeds - cost.
    Positive means profitable.

    Args:
        cost_base: What you spent in base currency.
        proceeds_base: What you received in base currency.

    Returns:
        Absolute profit in base currency units.
    """
    return proceeds_base - cost_base
