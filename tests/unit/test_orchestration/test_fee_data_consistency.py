"""Guard test: production and test fee_schedules.json structural consistency.

Verifies that both files cover the same set of venues and pairs in
withdrawal_fees and trading_accuracy sections. Values intentionally
differ (tests use deterministic data), but structural keys must match.

This prevents silent drift where one file adds a venue or pair that
the other lacks, which would cause runtime failures in production
but pass in tests (or vice versa).
"""

from __future__ import annotations

import importlib.resources
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def _load_production() -> dict:
    text = (
        importlib.resources.files("uscryptoarb.resources")
        .joinpath("fee_schedules.json")
        .read_text()
    )
    return json.loads(text)


def _load_test() -> dict:
    with open(FIXTURES_DIR / "fee_schedules.json") as f:
        return json.loads(f.read())


class TestFeeScheduleStructuralConsistency:
    """Verify structural keys match between production and test fee data."""

    def test_withdrawal_fees_venues_match(self) -> None:
        prod = set(_load_production()["withdrawal_fees"].keys())
        test = set(_load_test()["withdrawal_fees"].keys())
        assert prod == test, f"Venue mismatch in withdrawal_fees: prod={prod}, test={test}"

    def test_withdrawal_fees_currencies_match(self) -> None:
        prod = _load_production()["withdrawal_fees"]
        test = _load_test()["withdrawal_fees"]
        for venue in prod:
            prod_currencies = set(prod[venue].keys())
            test_currencies = set(test.get(venue, {}).keys())
            assert prod_currencies == test_currencies, (
                f"{venue} currency mismatch in withdrawal_fees: "
                f"prod={prod_currencies}, test={test_currencies}"
            )

    def test_trading_accuracy_venues_match(self) -> None:
        prod = set(_load_production()["trading_accuracy"].keys())
        test = set(_load_test()["trading_accuracy"].keys())
        assert prod == test, f"Venue mismatch in trading_accuracy: prod={prod}, test={test}"

    def test_trading_accuracy_pairs_match(self) -> None:
        prod = _load_production()["trading_accuracy"]
        test = _load_test()["trading_accuracy"]
        for venue in prod:
            prod_pairs = set(prod[venue].keys())
            test_pairs = set(test.get(venue, {}).keys())
            assert prod_pairs == test_pairs, (
                f"{venue} pair mismatch in trading_accuracy: prod={prod_pairs}, test={test_pairs}"
            )

    def test_trading_accuracy_field_keys_match(self) -> None:
        """Every accuracy entry should have the same set of fields."""
        prod = _load_production()["trading_accuracy"]
        test = _load_test()["trading_accuracy"]
        expected_fields = {
            "price_decimals",
            "lot_decimals",
            "min_order_size",
            "max_order_size",
            "tick_size",
            "lot_step",
        }
        for venue in prod:
            for pair in prod[venue]:
                prod_fields = set(prod[venue][pair].keys())
                test_fields = set(test.get(venue, {}).get(pair, {}).keys())
                assert prod_fields == expected_fields, f"prod {venue}/{pair} fields: {prod_fields}"
                assert test_fields == expected_fields, f"test {venue}/{pair} fields: {test_fields}"
