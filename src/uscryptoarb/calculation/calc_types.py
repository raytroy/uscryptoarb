"""
Immutable domain types for the calculation layer.

All dataclasses are frozen (immutable) and use slots for memory efficiency.
Decimal is used for all monetary values (DEC-007, LL-010).

These types are created via factory functions at data boundaries
(config loaders, connector parsers) and trusted downstream (DEC-003).

Mathematica equivalents:
    TradingFeeRate    → exchangeTradingFeesDatabase entries
    WithdrawalFee     → withdrawalDatabase entries
    TradingAccuracy   → tradingInfoDatabase entries / TradingAccuracyDataStructure[]
    FeeSchedule       → bundled fee context per (venue, pair)
    ArbLeg            → buy/sell side of ArbCalcFinal[]
    ArbOpportunity    → ArbCalcFinal[] output
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# ---------------------------------------------------------------------------
# Fee model types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TradingFeeRate:
    """Per-exchange, per-action trading fee rate.

    For Phase 1: flat rates from config.yaml (DEC-013).
    Future: tiered lookup based on 30-day volume.
    """

    venue: str  # "kraken", "coinbase", "gemini"
    action: str  # "buy" or "sell"
    pct_fee: Decimal  # e.g. Decimal("0.0026") for Kraken taker
    flat_fee: Decimal  # e.g. Decimal("0") — no flat trading fees


@dataclass(frozen=True, slots=True)
class WithdrawalFee:
    """Per-exchange, per-currency withdrawal cost.

    Withdrawal fees are denominated in the withdrawn currency.
    For crypto: typically a flat fee in the asset (e.g. 0.00005 BTC).
    For fiat (USD): typically a flat fee or percentage.

    Mathematica equivalent: withdrawalDatabase entries.
    """

    venue: str
    currency: str  # "BTC", "USD", "USDC", etc.
    flat_fee: Decimal  # e.g. Decimal("0.00005") for BTC on Kraken
    pct_fee: Decimal  # usually Decimal("0") for crypto withdrawals


@dataclass(frozen=True, slots=True)
class TradingAccuracy:
    """Per-exchange, per-pair precision constraints.

    Ensures order amounts and prices comply with exchange requirements.
    Data sourced from exchange API endpoints:
        Kraken:   AssetPairs → pair_decimals, lot_decimals, ordermin, tick_size
        Coinbase: Products   → quote_increment, base_increment, base_min_size

    Mathematica equivalent: TradingAccuracyDataStructure[].
    """

    venue: str
    pair: str  # canonical "BTC/USD"
    price_decimals: int  # Kraken pair_decimals / Coinbase derived from quote_increment
    lot_decimals: int  # Kraken lot_decimals / Coinbase from base_increment
    min_order_size: Decimal  # Kraken ordermin / Coinbase base_min_size
    max_order_size: Decimal | None  # Coinbase base_max_size; may be None
    tick_size: Decimal  # price step (Kraken tick_size / Coinbase quote_increment)
    lot_step: Decimal  # volume step (derived from lot_decimals or base_increment)


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    """Bundled fee and accuracy data for a single (venue, pair) combination.

    Passed to calculation functions as the complete fee context.
    Created once at startup from config, then reused for every scan cycle.
    """

    buy_fee: TradingFeeRate
    sell_fee: TradingFeeRate
    buy_withdrawal: WithdrawalFee | None  # withdrawal from buy exchange
    sell_withdrawal: WithdrawalFee | None  # withdrawal from sell exchange
    accuracy: TradingAccuracy


# ---------------------------------------------------------------------------
# Arbitrage result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArbLeg:
    """One side (buy or sell) of an arbitrage trade with full fee breakdown.

    Tracks the flow: MktCurrAmt → BaseCurrAmt → Grs → Net
    as defined in PROJECT_INSTRUCTIONS.md Section 6.5.

    Mathematica equivalent: part of ArbCalcFinal[] output.
    """

    venue: str
    pair: str  # canonical "BTC/USD"
    side: str  # "buy" or "sell"
    price: Decimal  # best ask (buy) or best bid (sell)
    mkt_curr_amt: Decimal  # market currency amount (e.g. BTC)
    base_curr_amt: Decimal  # base currency amount (e.g. USD)
    fee_rate: Decimal  # the pct fee applied
    trading_fee_base: Decimal  # absolute trading fee in base currency
    withdrawal_fee: Decimal  # absolute withdrawal fee in withdrawn currency


@dataclass(frozen=True, slots=True)
class ArbOpportunity:
    """Complete arbitrage opportunity evaluation.

    Contains all information needed to decide whether to execute:
    prices, returns at three levels (raw/gross/net), absolute profit,
    both legs with fee breakdowns, and the currency pair details.

    Mathematica equivalent: ArbCalcFinal[] output row.
    """

    pair: str  # canonical "BTC/USD"
    buy_venue: str
    sell_venue: str
    buy_price: Decimal  # best ask on buy exchange
    sell_price: Decimal  # best bid on sell exchange
    return_raw: Decimal  # (sell - buy) / buy — before fees
    return_grs: Decimal  # after trading fees
    return_net: Decimal  # after all fees (trading + withdrawal)
    profit_grs_base: Decimal  # absolute gross profit in base currency
    profit_net_base: Decimal  # absolute net profit in base currency
    buy_leg: ArbLeg
    sell_leg: ArbLeg
    market_currency: str  # e.g. "BTC"
    base_currency: str  # e.g. "USD"
    trade_amount: Decimal  # market currency amount traded
    ts_calculated_ms: int  # timestamp of calculation
