"""Tests for validation.guards module."""

from decimal import Decimal

import pytest

from uscryptoarb.validation.guards import (
    is_missing,
    require_non_negative,
    require_positive,
    require_present,
)


class TestIsMissing:
    """Tests for is_missing() function."""

    # --- Values that ARE missing ---

    def test_none_is_missing(self) -> None:
        assert is_missing(None) is True

    def test_empty_string_is_missing(self) -> None:
        assert is_missing("") is True

    def test_empty_list_is_missing(self) -> None:
        assert is_missing([]) is True

    def test_empty_dict_is_missing(self) -> None:
        assert is_missing({}) is True

    def test_empty_tuple_is_missing(self) -> None:
        assert is_missing(()) is True

    def test_empty_set_is_missing(self) -> None:
        assert is_missing(set()) is True

    def test_empty_frozenset_is_missing(self) -> None:
        assert is_missing(frozenset()) is True

    def test_decimal_nan_is_missing(self) -> None:
        assert is_missing(Decimal("NaN")) is True

    def test_decimal_infinity_is_missing(self) -> None:
        assert is_missing(Decimal("Infinity")) is True

    def test_decimal_negative_infinity_is_missing(self) -> None:
        assert is_missing(Decimal("-Infinity")) is True

    # --- Values that are NOT missing ---

    def test_zero_int_is_not_missing(self) -> None:
        assert is_missing(0) is False

    def test_zero_float_is_not_missing(self) -> None:
        assert is_missing(0.0) is False

    def test_zero_decimal_is_not_missing(self) -> None:
        assert is_missing(Decimal("0")) is False

    def test_positive_decimal_is_not_missing(self) -> None:
        assert is_missing(Decimal("123.456")) is False

    def test_negative_decimal_is_not_missing(self) -> None:
        assert is_missing(Decimal("-0.001")) is False

    def test_nonempty_string_is_not_missing(self) -> None:
        assert is_missing("BTC/USD") is False

    def test_whitespace_string_is_not_missing(self) -> None:
        assert is_missing("   ") is False

    def test_nonempty_list_is_not_missing(self) -> None:
        assert is_missing([1, 2, 3]) is False

    def test_nonempty_dict_is_not_missing(self) -> None:
        assert is_missing({"key": "value"}) is False

    def test_false_bool_is_not_missing(self) -> None:
        assert is_missing(False) is False

    def test_true_bool_is_not_missing(self) -> None:
        assert is_missing(True) is False


class TestRequirePresent:
    """Tests for require_present() function."""

    def test_returns_value_when_present(self) -> None:
        result = require_present("BTC/USD", "pair")
        assert result == "BTC/USD"

    def test_returns_zero_when_present(self) -> None:
        result = require_present(0, "count")
        assert result == 0

    def test_returns_decimal_when_present(self) -> None:
        price = Decimal("100.50")
        result = require_present(price, "price")
        assert result == price

    def test_raises_for_none(self) -> None:
        with pytest.raises(ValueError, match="Required value 'price' is missing"):
            require_present(None, "price")

    def test_raises_for_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Required value 'venue' is missing"):
            require_present("", "venue")

    def test_raises_for_empty_list(self) -> None:
        with pytest.raises(ValueError, match="Required value 'levels' is missing"):
            require_present([], "levels")

    def test_raises_for_decimal_nan(self) -> None:
        with pytest.raises(ValueError, match="Required value 'amount' is missing"):
            require_present(Decimal("NaN"), "amount")


class TestRequirePositive:
    """Tests for require_positive() function."""

    def test_returns_positive_decimal(self) -> None:
        result = require_positive(Decimal("100.50"), "price")
        assert result == Decimal("100.50")

    def test_returns_small_positive(self) -> None:
        result = require_positive(Decimal("0.00000001"), "fee")
        assert result == Decimal("0.00000001")

    def test_raises_for_zero(self) -> None:
        with pytest.raises(ValueError, match="'price' must be positive"):
            require_positive(Decimal("0"), "price")

    def test_raises_for_negative(self) -> None:
        with pytest.raises(ValueError, match="'price' must be positive"):
            require_positive(Decimal("-1"), "price")

    def test_raises_for_none(self) -> None:
        with pytest.raises(ValueError, match="Required value 'price' is missing"):
            require_positive(None, "price")  # type: ignore[arg-type]

    def test_raises_for_nan(self) -> None:
        with pytest.raises(ValueError, match="Required value 'price' is missing"):
            require_positive(Decimal("NaN"), "price")


class TestRequireNonNegative:
    """Tests for require_non_negative() function."""

    def test_returns_positive_decimal(self) -> None:
        result = require_non_negative(Decimal("100"), "balance")
        assert result == Decimal("100")

    def test_returns_zero(self) -> None:
        result = require_non_negative(Decimal("0"), "balance")
        assert result == Decimal("0")

    def test_raises_for_negative(self) -> None:
        with pytest.raises(ValueError, match="'balance' must be non-negative"):
            require_non_negative(Decimal("-0.01"), "balance")

    def test_raises_for_none(self) -> None:
        with pytest.raises(ValueError, match="Required value 'balance' is missing"):
            require_non_negative(None, "balance")  # type: ignore[arg-type]

    def test_raises_for_nan(self) -> None:
        with pytest.raises(ValueError, match="Required value 'balance' is missing"):
            require_non_negative(Decimal("NaN"), "balance")
