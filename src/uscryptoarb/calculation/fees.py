"""
Fee calculation functions for arbitrage trade legs.

Implements the Mathematica fee flow from PROJECT_INSTRUCTIONS.md Section 6.5:

    Buy Side (you're buying market currency, paying base currency):
        MktCurrAmt = trade_amount
        BaseCurrAmt = MktCurrAmt × buy_price
        BaseCurrAmtGrs = BaseCurrAmt × (1 + buy_fee_pct)   # fee increases cost

    Sell Side (you're selling market currency, receiving base currency):
        MktCurrAmt = trade_amount
        BaseCurrAmt = MktCurrAmt × sell_price
        BaseCurrAmtGrs = BaseCurrAmt × (1 - sell_fee_pct)  # fee reduces proceeds

    Net (after withdrawal):
        amount_net = amount_grs - withdrawal_flat_fee - (amount_grs × withdrawal_pct_fee)

The key insight: buy fee makes your cost HIGHER, sell fee makes your
proceeds LOWER. Both reduce your profit.

All functions are pure. No validation (DEC-003, LL-020).
All monetary values use Decimal (DEC-007, LL-010).

Mathematica equivalents:
    calc_buy_side[]  → calc_buy_leg
    calc_sell_side[] → calc_sell_leg
    withdrawal fee application within CalcArbAmount[]
"""

from __future__ import annotations

from decimal import Decimal

from uscryptoarb.calculation.types import ArbLeg, WithdrawalFee

ZERO = Decimal("0")


def calc_buy_leg(
    *,
    venue: str,
    pair: str,
    price: Decimal,
    amount: Decimal,
    fee_pct: Decimal,
    flat_fee: Decimal = ZERO,
    withdrawal: WithdrawalFee | None = None,
) -> ArbLeg:
    """Calculate buy-side leg with fee breakdown.

    You are BUYING market currency (e.g. BTC) and PAYING in base
    currency (e.g. USD). The trading fee increases your total cost.

    Fee flow:
        base_cost = amount × price
        trading_fee = base_cost × fee_pct + flat_fee
        total_cost = base_cost × (1 + fee_pct)

    Withdrawal fee (if transferring market currency out of buy exchange):
        withdrawal reduces the market currency you actually have.

    Args:
        venue: Exchange name (e.g. "kraken").
        pair: Canonical pair (e.g. "BTC/USD").
        price: Best ask price (what you pay per unit).
        amount: Market currency amount to buy (e.g. 0.1 BTC).
        fee_pct: Trading fee as a decimal fraction (e.g. 0.0026).
        flat_fee: Fixed trading fee in base currency.
        withdrawal: Optional withdrawal fee for market currency.

    Returns:
        ArbLeg with complete fee breakdown.
    """
    base_cost = amount * price
    trading_fee = base_cost * fee_pct + flat_fee

    # Withdrawal fee on market currency (if moving crypto off buy exchange)
    w_fee = ZERO
    if withdrawal is not None:
        w_fee = withdrawal.flat_fee + (amount * withdrawal.pct_fee)

    return ArbLeg(
        venue=venue,
        pair=pair,
        side="buy",
        price=price,
        mkt_curr_amt=amount,
        base_curr_amt=base_cost,
        fee_rate=fee_pct,
        trading_fee_base=trading_fee,
        withdrawal_fee=w_fee,
    )


def calc_sell_leg(
    *,
    venue: str,
    pair: str,
    price: Decimal,
    amount: Decimal,
    fee_pct: Decimal,
    flat_fee: Decimal = ZERO,
    withdrawal: WithdrawalFee | None = None,
) -> ArbLeg:
    """Calculate sell-side leg with fee breakdown.

    You are SELLING market currency (e.g. BTC) and RECEIVING base
    currency (e.g. USD). The trading fee reduces your proceeds.

    Fee flow:
        base_proceeds = amount × price
        trading_fee = base_proceeds × fee_pct + flat_fee
        net_proceeds = base_proceeds × (1 - fee_pct)

    Withdrawal fee (if transferring base currency out of sell exchange):
        withdrawal reduces the base currency you actually receive.

    Args:
        venue: Exchange name (e.g. "coinbase").
        pair: Canonical pair (e.g. "BTC/USD").
        price: Best bid price (what you receive per unit).
        amount: Market currency amount to sell (e.g. 0.1 BTC).
        fee_pct: Trading fee as a decimal fraction (e.g. 0.006).
        flat_fee: Fixed trading fee in base currency.
        withdrawal: Optional withdrawal fee for base currency.

    Returns:
        ArbLeg with complete fee breakdown.
    """
    base_proceeds = amount * price
    trading_fee = base_proceeds * fee_pct + flat_fee

    # Withdrawal fee on base currency (if moving fiat/stablecoin off sell exchange)
    w_fee = ZERO
    if withdrawal is not None:
        w_fee = withdrawal.flat_fee + (base_proceeds * withdrawal.pct_fee)

    return ArbLeg(
        venue=venue,
        pair=pair,
        side="sell",
        price=price,
        mkt_curr_amt=amount,
        base_curr_amt=base_proceeds,
        fee_rate=fee_pct,
        trading_fee_base=trading_fee,
        withdrawal_fee=w_fee,
    )


def effective_buy_cost(leg: ArbLeg) -> Decimal:
    """Total base currency cost for buy leg (cost + trading fee).

    This is BaseCurrAmtGrs = BaseCurrAmt × (1 + fee_pct).
    """
    return leg.base_curr_amt + leg.trading_fee_base


def effective_sell_proceeds(leg: ArbLeg) -> Decimal:
    """Net base currency proceeds for sell leg (proceeds - trading fee).

    This is BaseCurrAmtGrs = BaseCurrAmt × (1 - fee_pct).
    """
    return leg.base_curr_amt - leg.trading_fee_base


def total_buy_cost(leg: ArbLeg) -> Decimal:
    """Total cost including trading fee and withdrawal fee.

    For buy side: you pay base currency (trading fee in base)
    plus you lose some market currency to withdrawal fee.
    The withdrawal fee on market currency is converted to base at the leg price.
    """
    base_cost = effective_buy_cost(leg)
    # Convert market currency withdrawal fee to base currency
    withdrawal_in_base = leg.withdrawal_fee * leg.price
    return base_cost + withdrawal_in_base


def net_sell_proceeds(leg: ArbLeg) -> Decimal:
    """Net proceeds after trading fee and withdrawal fee.

    For sell side: you receive base currency (minus trading fee)
    minus withdrawal fee on base currency.
    """
    return effective_sell_proceeds(leg) - leg.withdrawal_fee
