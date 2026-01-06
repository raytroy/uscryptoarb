"""
Runtime validation guards for data boundaries.

PATTERN: "Validate at Boundaries, Trust Downstream"
=========================================================

Validation happens ONLY at data boundaries:
    - Connector parse_*/fetch_* functions (API responses)
    - Factory functions like tob_from_raw() (raw → domain type)
    - Config loaders (YAML/env → AppConfig)
    - Dataclass __post_init__ methods (critical invariants)

Validation does NOT happen in:
    - calculation/ modules — just math on validated types
    - strategy/ modules — just logic on validated types

If you're adding require_* calls in calculation or strategy,
something is wrong upstream. Fix the boundary instead.

GUARDS API:
    is_missing(value) -> bool
        True for: None, "", [], {}, (), set(), Decimal("NaN"), Decimal("Inf")
        False for: 0, False, Decimal("0"), "   " (whitespace)

    require_present(value, name) -> T
        Raise ValueError if missing, else return value unchanged.
        Use for: required fields that must exist.

    require_positive(value, name) -> Decimal
        Raise ValueError if missing, zero, or negative.
        Use for: prices, fees, sizes (must be > 0).

    require_non_negative(value, name) -> Decimal
        Raise ValueError if missing or negative. Zero is allowed.
        Use for: balances, quantities (can be 0).

EXAMPLE - Factory Function (the primary validation boundary):

    def tob_from_raw(*, venue: str, pair: str, bid_px: DecimalLike, ...) -> TopOfBook:
        t = TopOfBook(
            venue=venue,
            pair=pair,
            bid_px=to_decimal(bid_px),  # Rejects floats
            ...
        )
        validate_tob(t)  # Checks invariants
        return t

    # Connector uses factory — validation happens HERE
    async def fetch_ticker(self, pair: str) -> TopOfBook:
        raw = await api.get_ticker(pair)
        return tob_from_raw(venue="kraken", pair=pair, bid_px=raw["bid"], ...)

    # Calculation trusts input — NO validation
    def calc_spread(tob: TopOfBook) -> Decimal:
        return tob.ask_px - tob.bid_px

See PROJECT_INSTRUCTIONS.md Section 6.2 for full documentation.

Mathematica equivalent: MissingCheck[]
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, TypeVar

T = TypeVar("T")


def is_missing(value: Any) -> bool:
    """
    Check if a value is considered "missing" for arbitrage calculations.

    A value is missing if:
    - It is None
    - It is an empty string ""
    - It is an empty collection (list, dict, tuple, set, frozenset)
    - It is a non-finite Decimal (NaN, Infinity, -Infinity)

    Note: Zero is NOT missing. False is NOT missing. These are valid values.

    This is equivalent to Mathematica's MissingCheck[] function.

    Args:
        value: Any value to check

    Returns:
        True if the value is missing, False otherwise

    Examples:
        >>> is_missing(None)
        True
        >>> is_missing("")
        True
        >>> is_missing([])
        True
        >>> is_missing(Decimal("NaN"))
        True
        >>> is_missing(0)
        False
        >>> is_missing(Decimal("0"))
        False
    """
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    if isinstance(value, (list, dict, tuple, set, frozenset)) and len(value) == 0:
        return True
    if isinstance(value, Decimal) and not value.is_finite():
        return True
    return False


def require_present(value: T, name: str) -> T:
    """
    Require that a value is present (not missing).

    Returns the value unchanged if present, raises ValueError if missing.
    Use at data boundaries to enforce that required values exist.

    Args:
        value: The value to check
        name: Descriptive name for error messages

    Returns:
        The value unchanged if not missing

    Raises:
        ValueError: If the value is missing

    Examples:
        >>> require_present("BTC/USD", "pair")
        'BTC/USD'
        >>> require_present(None, "price")
        Traceback (most recent call last):
        ValueError: Required value 'price' is missing
    """
    if is_missing(value):
        raise ValueError(f"Required value '{name}' is missing")
    return value


def require_positive(value: Decimal, name: str) -> Decimal:
    """
    Require that a Decimal value is positive (> 0).

    Use for prices, sizes, fees, and other values that must be strictly positive.

    Args:
        value: The Decimal to check
        name: Descriptive name for error messages

    Returns:
        The value unchanged if positive

    Raises:
        ValueError: If missing, zero, or negative

    Examples:
        >>> require_positive(Decimal("100.50"), "price")
        Decimal('100.50')
        >>> require_positive(Decimal("0"), "price")
        Traceback (most recent call last):
        ValueError: 'price' must be positive, got 0
    """
    if is_missing(value):
        raise ValueError(f"Required value '{name}' is missing")
    if value <= 0:
        raise ValueError(f"'{name}' must be positive, got {value}")
    return value


def require_non_negative(value: Decimal, name: str) -> Decimal:
    """
    Require that a Decimal value is non-negative (>= 0).

    Use for balances, quantities, and values that can be zero but not negative.

    Args:
        value: The Decimal to check
        name: Descriptive name for error messages

    Returns:
        The value unchanged if non-negative

    Raises:
        ValueError: If missing or negative

    Examples:
        >>> require_non_negative(Decimal("0"), "balance")
        Decimal('0')
        >>> require_non_negative(Decimal("-1"), "balance")
        Traceback (most recent call last):
        ValueError: 'balance' must be non-negative, got -1
    """
    if is_missing(value):
        raise ValueError(f"Required value '{name}' is missing")
    if value < 0:
        raise ValueError(f"'{name}' must be non-negative, got {value}")
    return value
