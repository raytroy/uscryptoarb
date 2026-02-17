import json
from decimal import Decimal
from pathlib import Path

from uscryptoarb.calculation.calc_types import ArbLeg, ArbOpportunity

"""Shared test utilities (not fixtures — those go in conftest.py)."""


class DummyRateLimiter:
    """Test double for RateLimiter. Counts calls but never waits."""

    def __init__(self) -> None:
        self.calls = 0

    async def acquire(self) -> None:
        self.calls += 1


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file from tests/fixtures/.

    Centralized helper replacing per-module copies in parser test files.
    """
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def make_arb_opportunity(**overrides: object) -> ArbOpportunity:
    """Build an ArbOpportunity with sensible defaults for testing.

    Pass keyword arguments to override any field. Example:
        make_arb_opportunity(return_net=Decimal("0.02"), pair="LTC/USD")
    """
    default_leg = ArbLeg(
        venue="kraken",
        pair="BTC/USD",
        side="buy",
        price=Decimal("100"),
        mkt_curr_amt=Decimal("1"),
        base_curr_amt=Decimal("100"),
        fee_rate=Decimal("0.001"),
        trading_fee_base=Decimal("0.1"),
        withdrawal_fee=Decimal("0"),
    )
    defaults: dict[str, object] = {
        "pair": "BTC/USD",
        "buy_venue": "kraken",
        "sell_venue": "coinbase",
        "buy_price": Decimal("100"),
        "sell_price": Decimal("101"),
        "return_raw": Decimal("0.01"),
        "return_grs": Decimal("0.009"),
        "return_net": Decimal("0.008"),
        "profit_grs_base": Decimal("1.0"),
        "profit_net_base": Decimal("0.8"),
        "buy_leg": default_leg,
        "sell_leg": default_leg,
        "market_currency": "BTC",
        "base_currency": "USD",
        "trade_amount": Decimal("1"),
        "ts_calculated_ms": 1707900000000,
    }
    defaults.update(overrides)
    return ArbOpportunity(**defaults)  # type: ignore[arg-type]
