"""Tests for CEX.IO symbol mapping."""

import pytest

from uscryptoarb.connectors.cexio.symbols import CEXIO_SYMBOL_MAP, CEXIO_SYMBOLS


def test_forward_lookup_all_pairs() -> None:
    for canonical, expected in CEXIO_SYMBOL_MAP.items():
        assert CEXIO_SYMBOLS.to_venue_symbol(canonical) == expected


def test_reverse_lookup_all_pairs() -> None:
    for canonical, venue_sym in CEXIO_SYMBOL_MAP.items():
        assert CEXIO_SYMBOLS.to_canonical(venue_sym) == canonical


def test_unknown_canonical_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        CEXIO_SYMBOLS.to_venue_symbol("UNKNOWN/PAIR")


def test_symbol_map_has_exactly_eight_entries() -> None:
    assert len(CEXIO_SYMBOL_MAP) == 8


def test_round_trip_all_pairs() -> None:
    for canonical in CEXIO_SYMBOL_MAP:
        venue_sym = CEXIO_SYMBOLS.to_venue_symbol(canonical)
        back = CEXIO_SYMBOLS.to_canonical(venue_sym)
        assert back == canonical


def test_usd_usdc_distinct() -> None:
    """USD and USDC map to distinct venue symbols (DEC-001)."""
    usd_sym = CEXIO_SYMBOLS.to_venue_symbol("BTC/USD")
    usdc_sym = CEXIO_SYMBOLS.to_venue_symbol("BTC/USDC")
    assert usd_sym != usdc_sym
