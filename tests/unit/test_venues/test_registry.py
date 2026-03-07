"""Tests for venues/registry.py — Ohio-eligible venue filtering."""

import pytest

from uscryptoarb.venues.registry import ohio_eligible


def test_ohio_eligible_ok() -> None:
    venues = ["kraken", "coinbase", "gemini", "bitstamp", "okx", "cexio", "cryptodotcom"]
    result = ohio_eligible(venues)
    assert list(result) == venues


def test_ohio_eligible_unknown_rejected() -> None:
    with pytest.raises(ValueError):
        ohio_eligible(["kraken", "unknown_exchange", "coinbase"])
