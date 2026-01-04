from decimal import Decimal

import pytest

from uscryptoarb.misc.decimals import ceil_to_step, floor_to_step, to_decimal


def test_d_rejects_float() -> None:
    with pytest.raises(TypeError):
        to_decimal(1.23)  # type: ignore[arg-type]


def test_floor_to_step() -> None:
    assert floor_to_step(Decimal("1.239"), Decimal("0.01")) == Decimal("1.23")
    assert floor_to_step(Decimal("1.239"), Decimal("0.1")) == Decimal("1.2")


def test_ceil_to_step() -> None:
    assert ceil_to_step(Decimal("1.231"), Decimal("0.01")) == Decimal("1.24")
    assert ceil_to_step(Decimal("1.201"), Decimal("0.1")) == Decimal("1.3")
