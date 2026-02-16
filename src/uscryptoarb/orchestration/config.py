from __future__ import annotations

import importlib.resources
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

import yaml
from dotenv import load_dotenv
from uscryptoarb.calculation.types import (
    FeeSchedule,
    TradingAccuracy,
    TradingFeeRate,
    WithdrawalFee,
)
from uscryptoarb.markets.pairs import parse_pair
from uscryptoarb.misc.decimals import to_decimal
from uscryptoarb.notification.email import EmailConfig
from uscryptoarb.validation import require_present
from uscryptoarb.venues.registry import ohio_eligible

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ArbitrageConfig:
    threshold: Decimal
    trade_amounts: dict[str, Decimal]
    max_staleness_ms: int
    min_bankroll_limit: Decimal


@dataclass(frozen=True, slots=True)
class PollingConfig:
    interval_seconds: int
    max_concurrent_requests: int


@dataclass(frozen=True, slots=True)
class VenueConnectorConfig:
    rate_limit_ms: int
    timeout_s: float
    max_retries: int


@dataclass(frozen=True, slots=True)
class DebugConfig:
    enabled: bool
    trace_pairs: tuple[str, ...]
    log_level: str


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    venues: tuple[str, ...]
    pairs: tuple[str, ...]
    arbitrage: ArbitrageConfig
    polling: PollingConfig
    venue_configs: dict[str, VenueConnectorConfig]
    email: EmailConfig
    debug: DebugConfig
    # Pragmatic mutability exception: nested dicts are treated immutable by convention.
    fees_by_pair_venue: dict[str, dict[str, FeeSchedule]]


_DEFAULT_VENUE_CONFIG = VenueConnectorConfig(rate_limit_ms=500, timeout_s=10.0, max_retries=3)


def _required_type(value: Any, name: str, converter: Callable[[Any], _T]) -> _T:
    """Validate presence and convert to target type.

    Replaces the previous _required_decimal() and _required_int() helpers
    with a single generic. Raises ValueError if value is missing.
    """
    return converter(require_present(value, name))


def load_config(path: str = "config.yaml") -> ScannerConfig:
    load_dotenv()

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw_obj = yaml.safe_load(config_path.read_text())
    if not isinstance(raw_obj, dict):
        raise ValueError("Config must be a YAML mapping")

    venues_section = require_present(raw_obj.get("venues"), "venues")
    if not isinstance(venues_section, dict):
        raise ValueError("venues must be a mapping")

    venues_raw = require_present(venues_section.get("primary"), "venues.primary")
    if not isinstance(venues_raw, list):
        raise ValueError("venues.primary must be a list")
    venues = tuple(ohio_eligible(venues_raw))

    pairs_raw = require_present(raw_obj.get("pairs"), "pairs")
    if not isinstance(pairs_raw, list):
        raise ValueError("pairs must be a list")
    if not pairs_raw:
        raise ValueError("pairs must be non-empty")

    pairs: list[str] = []
    for pair in pairs_raw:
        parsed = parse_pair(str(pair))
        pairs.append(parsed.as_str)

    arbitrage_raw = raw_obj.get("arbitrage", {})
    if not isinstance(arbitrage_raw, dict):
        raise ValueError("arbitrage must be a mapping")

    threshold_raw = require_present(arbitrage_raw.get("threshold"), "arbitrage.threshold")
    trade_amounts_raw = require_present(
        arbitrage_raw.get("trade_amounts"),
        "arbitrage.trade_amounts",
    )
    if not isinstance(trade_amounts_raw, dict):
        raise ValueError("arbitrage.trade_amounts must be a mapping")

    trade_amounts: dict[str, Decimal] = {}
    for pair in pairs:
        raw_amt = trade_amounts_raw.get(pair)
        if raw_amt is None:
            raise ValueError(f"Missing trade_amounts entry for pair: {pair}")
        trade_amounts[pair] = to_decimal(raw_amt)

    arbitrage_cfg = ArbitrageConfig(
        threshold=_required_type(threshold_raw, "arbitrage.threshold", to_decimal),
        trade_amounts=trade_amounts,
        max_staleness_ms=int(arbitrage_raw.get("max_staleness_ms", 5000)),
        min_bankroll_limit=_required_type(
            arbitrage_raw.get("min_bankroll_limit", "0.10"),
            "arbitrage.min_bankroll_limit",
            to_decimal,
        ),
    )

    polling_raw = raw_obj.get("polling", {})
    if not isinstance(polling_raw, dict):
        raise ValueError("polling must be a mapping")
    polling_cfg = PollingConfig(
        interval_seconds=int(polling_raw.get("interval_seconds", 5)),
        max_concurrent_requests=int(polling_raw.get("max_concurrent_requests", 10)),
    )

    venue_configs_raw = raw_obj.get("venue_configs", {})
    if not isinstance(venue_configs_raw, dict):
        raise ValueError("venue_configs must be a mapping")

    venue_configs: dict[str, VenueConnectorConfig] = {}
    for venue in venues:
        venue_raw = venue_configs_raw.get(venue, {})
        if not isinstance(venue_raw, dict):
            raise ValueError(f"venue_configs.{venue} must be a mapping")
        venue_configs[venue] = VenueConnectorConfig(
            rate_limit_ms=int(venue_raw.get("rate_limit_ms", _DEFAULT_VENUE_CONFIG.rate_limit_ms)),
            timeout_s=float(venue_raw.get("timeout_s", _DEFAULT_VENUE_CONFIG.timeout_s)),
            max_retries=int(venue_raw.get("max_retries", _DEFAULT_VENUE_CONFIG.max_retries)),
        )

    notifications_raw = raw_obj.get("notifications", {})
    email_raw = notifications_raw.get("email", {}) if isinstance(notifications_raw, dict) else {}
    if not isinstance(email_raw, dict):
        raise ValueError("notifications.email must be a mapping")

    recipients = email_raw.get("recipients", [])
    if not isinstance(recipients, list):
        raise ValueError("notifications.email.recipients must be a list")

    email_cfg = EmailConfig(
        enabled=bool(email_raw.get("enabled", False)),
        smtp_host=str(email_raw.get("smtp_host", "smtp.gmail.com")),
        smtp_port=int(email_raw.get("smtp_port", 587)),
        from_addr=os.getenv("SMTP_FROM_ADDR", ""),
        recipients=tuple(str(r) for r in recipients),
        password=os.getenv("SMTP_PASSWORD", ""),
    )

    debug_raw = raw_obj.get("debug", {})
    if not isinstance(debug_raw, dict):
        raise ValueError("debug must be a mapping")
    trace_pairs_raw = debug_raw.get("trace_pairs", [])
    if not isinstance(trace_pairs_raw, list):
        raise ValueError("debug.trace_pairs must be a list")
    debug_cfg = DebugConfig(
        enabled=bool(debug_raw.get("enabled", False)),
        trace_pairs=tuple(str(p) for p in trace_pairs_raw),
        log_level=str(debug_raw.get("log_level", "INFO")),
    )

    fee_data_text = (
        importlib.resources.files("uscryptoarb.resources")
        .joinpath("fee_schedules.json")
        .read_text()
    )
    fee_data = json.loads(fee_data_text)
    fees_by_pair_venue = _build_fee_schedules(
        pairs=pairs,
        venues=venues,
        fees_cfg=raw_obj.get("fees", {}),
        fee_data=fee_data,
    )

    return ScannerConfig(
        venues=venues,
        pairs=tuple(pairs),
        arbitrage=arbitrage_cfg,
        polling=polling_cfg,
        venue_configs=venue_configs,
        email=email_cfg,
        debug=debug_cfg,
        fees_by_pair_venue=fees_by_pair_venue,
    )


def _build_fee_schedules(
    *,
    pairs: list[str],
    venues: tuple[str, ...],
    fees_cfg: Any,
    fee_data: dict[str, Any],
) -> dict[str, dict[str, FeeSchedule]]:
    if not isinstance(fees_cfg, dict):
        raise ValueError("fees must be a mapping")

    withdrawal_fees = fee_data.get("withdrawal_fees", {})
    accuracy_data = fee_data.get("trading_accuracy", {})
    if not isinstance(withdrawal_fees, dict) or not isinstance(accuracy_data, dict):
        raise ValueError("fee_schedules.json missing withdrawal_fees/trading_accuracy mappings")

    out: dict[str, dict[str, FeeSchedule]] = {}
    for pair in pairs:
        parsed = parse_pair(pair)
        market_currency = parsed.base
        base_currency = parsed.quote
        out[pair] = {}

        for venue in venues:
            venue_fee_cfg = fees_cfg.get(venue, {})
            if not isinstance(venue_fee_cfg, dict):
                raise ValueError(f"fees.{venue} must be a mapping")

            buy_rate_raw = require_present(venue_fee_cfg.get("buy"), f"fees.{venue}.buy")
            sell_rate_raw = require_present(venue_fee_cfg.get("sell"), f"fees.{venue}.sell")

            venue_withdrawals = withdrawal_fees.get(venue)
            venue_accuracy = accuracy_data.get(venue)
            if not isinstance(venue_withdrawals, dict) or not isinstance(venue_accuracy, dict):
                logger.warning(
                    "Skipping fee schedule for %s/%s due to missing withdrawal/accuracy venue data",
                    venue,
                    pair,
                )
                continue

            buy_withdrawal_raw = venue_withdrawals.get(market_currency)
            sell_withdrawal_raw = venue_withdrawals.get(base_currency)
            accuracy_raw = venue_accuracy.get(pair)

            if not isinstance(buy_withdrawal_raw, dict) or not isinstance(
                sell_withdrawal_raw, dict
            ):
                logger.warning(
                    "Skipping fee schedule for %s/%s due to missing withdrawal data",
                    venue,
                    pair,
                )
                continue
            if not isinstance(accuracy_raw, dict):
                logger.warning(
                    "Skipping fee schedule for %s/%s due to missing trading accuracy data",
                    venue,
                    pair,
                )
                continue

            out[pair][venue] = FeeSchedule(
                buy_fee=TradingFeeRate(
                    venue=venue,
                    action="buy",
                    pct_fee=_required_type(buy_rate_raw, f"fees.{venue}.buy", to_decimal),
                    flat_fee=Decimal("0"),
                ),
                sell_fee=TradingFeeRate(
                    venue=venue,
                    action="sell",
                    pct_fee=_required_type(sell_rate_raw, f"fees.{venue}.sell", to_decimal),
                    flat_fee=Decimal("0"),
                ),
                buy_withdrawal=WithdrawalFee(
                    venue=venue,
                    currency=market_currency,
                    flat_fee=_required_type(
                        buy_withdrawal_raw.get("flat_fee"), "flat_fee", to_decimal
                    ),
                    pct_fee=_required_type(
                        buy_withdrawal_raw.get("pct_fee"), "pct_fee", to_decimal
                    ),
                ),
                sell_withdrawal=WithdrawalFee(
                    venue=venue,
                    currency=base_currency,
                    flat_fee=_required_type(
                        sell_withdrawal_raw.get("flat_fee"), "flat_fee", to_decimal
                    ),
                    pct_fee=_required_type(
                        sell_withdrawal_raw.get("pct_fee"), "pct_fee", to_decimal
                    ),
                ),
                accuracy=TradingAccuracy(
                    venue=venue,
                    pair=pair,
                    price_decimals=_required_type(
                        accuracy_raw.get("price_decimals"), "price_decimals", int
                    ),
                    lot_decimals=_required_type(
                        accuracy_raw.get("lot_decimals"), "lot_decimals", int
                    ),
                    min_order_size=_required_type(
                        accuracy_raw.get("min_order_size"), "min_order_size", to_decimal
                    ),
                    max_order_size=(
                        to_decimal(accuracy_raw["max_order_size"])
                        if accuracy_raw.get("max_order_size") is not None
                        else None
                    ),
                    tick_size=_required_type(
                        accuracy_raw.get("tick_size"), "tick_size", to_decimal
                    ),
                    lot_step=_required_type(accuracy_raw.get("lot_step"), "lot_step", to_decimal),
                ),
            )

    return out
