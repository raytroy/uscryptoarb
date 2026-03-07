"""Tests for Crypto.com symbol mapping."""

import pytest

from uscryptoarb.connectors.cryptodotcom.symbols import (
    CRYPTODOTCOM_SYMBOL_MAP,
    CRYPTODOTCOM_SYMBOLS,
)


def test_forward_lookup_all_pairs() -> None:
    for canonical, expected in CRYPTODOTCOM_SYMBOL_MAP.items():
        assert CRYPTODOTCOM_SYMBOLS.to_venue_symbol(canonical) == expected


def test_reverse_lookup_all_pairs() -> None:
    for canonical, venue_sym in CRYPTODOTCOM_SYMBOL_MAP.items():
        assert CRYPTODOTCOM_SYMBOLS.to_canonical(venue_sym) == canonical


def test_unknown_canonical_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        CRYPTODOTCOM_SYMBOLS.to_venue_symbol("UNKNOWN/PAIR")


def test_symbol_map_has_exactly_five_entries() -> None:
    assert len(CRYPTODOTCOM_SYMBOL_MAP) == 5


def test_usdc_pairs_deliberately_absent() -> None:
    """BTC/USDC, LTC/USDC, SOL/USDC not listed on Crypto.com Exchange."""
    for pair in ("BTC/USDC", "LTC/USDC", "SOL/USDC"):
        assert pair not in CRYPTODOTCOM_SYMBOL_MAP


def test_round_trip_all_pairs() -> None:
    for canonical in CRYPTODOTCOM_SYMBOL_MAP:
        venue_sym = CRYPTODOTCOM_SYMBOLS.to_venue_symbol(canonical)
        back = CRYPTODOTCOM_SYMBOLS.to_canonical(venue_sym)
        assert back == canonical


def test_underscore_format() -> None:
    """Crypto.com uses underscore-separated symbols."""
    assert CRYPTODOTCOM_SYMBOLS.to_venue_symbol("BTC/USD") == "BTC_USD"
    assert CRYPTODOTCOM_SYMBOLS.to_venue_symbol("SOL/BTC") == "SOL_BTC"
