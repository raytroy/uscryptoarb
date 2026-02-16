import pytest

from uscryptoarb.connectors.gemini.symbols import (
    GEMINI_SYMBOL_MAP,
    GEMINI_SYMBOLS,
)


def test_forward_lookup_all_pairs() -> None:
    for canonical, expected in GEMINI_SYMBOL_MAP.items():
        assert GEMINI_SYMBOLS.to_venue_symbol(canonical) == expected


def test_reverse_lookup_all_pairs() -> None:
    for canonical, venue_sym in GEMINI_SYMBOL_MAP.items():
        assert GEMINI_SYMBOLS.to_canonical(venue_sym) == canonical


def test_unknown_pair_raises() -> None:
    with pytest.raises(KeyError, match="gemini"):
        GEMINI_SYMBOLS.to_venue_symbol("ETH/USD")


def test_symbol_map_has_eight_pairs() -> None:
    assert len(GEMINI_SYMBOL_MAP) == 8


def test_unknown_venue_symbol_raises() -> None:
    with pytest.raises(KeyError, match="gemini"):
        GEMINI_SYMBOLS.to_canonical("fakepair")
