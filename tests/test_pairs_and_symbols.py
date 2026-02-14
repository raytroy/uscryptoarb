import pytest

from uscryptoarb.markets.pairs import parse_pair
from uscryptoarb.venues.symbols import SymbolTranslator


def test_parse_pair_normalizes() -> None:
    p = parse_pair(" sol / usdc ")
    assert p.base == "SOL"
    assert p.quote == "USDC"
    assert p.as_str == "SOL/USDC"


def test_symbol_translator_happy_path() -> None:
    tr = SymbolTranslator(
        venue="example",
        canonical_to_venue={"SOL/USDC": "SOLUSDC"},
    )
    assert tr.to_venue_symbol("SOL/USDC") == "SOLUSDC"


def test_symbol_translator_missing_mapping() -> None:
    tr = SymbolTranslator(venue="example", canonical_to_venue={})
    with pytest.raises(KeyError):
        tr.to_venue_symbol("BTC/USD")


def test_symbol_translator_reverse_lookup() -> None:
    tr = SymbolTranslator(venue="example", canonical_to_venue={"BTC/USD": "XXBTZUSD"})
    assert tr.to_canonical("XXBTZUSD") == "BTC/USD"


def test_symbol_translator_reverse_missing() -> None:
    tr = SymbolTranslator(venue="example", canonical_to_venue={})
    with pytest.raises(KeyError):
        tr.to_canonical("XXBTZUSD")
