from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Union


DecimalLike = Union[Decimal, str, int, float]


def to_decimal(x: DecimalLike) -> Decimal:
    """
    Safe Decimal constructor.

    - Rejects float inputs (silent float->str conversions are easy to mess up).
    - Accepts Decimal, str, int.
    """
    if isinstance(x, float):
        raise TypeError("float is not allowed; pass Decimal, str, or int")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    """
    Quantize DOWN to the nearest multiple of `step`.
    Intended for non-negative money/size values.
    """
    if step <= 0:
        raise ValueError("step must be > 0")
    if value < 0:
        raise ValueError("value must be >= 0")
    q = (value / step).to_integral_value(rounding=ROUND_DOWN)
    return q * step


def ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    """
    Quantize UP to the nearest multiple of `step`.
    Intended for non-negative money/size values.
    """
    if step <= 0:
        raise ValueError("step must be > 0")
    if value < 0:
        raise ValueError("value must be >= 0")
    q = (value / step).to_integral_value(rounding=ROUND_UP)
    return q * step
