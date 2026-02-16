import pytest

from uscryptoarb.markets.pairs import parse_pair
from uscryptoarb.venues.symbols import SymbolTranslator, create_translator


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


def test_create_translator_happy_path() -> None:
    t = create_translator("test_venue", {"BTC/USD": "BTC-USD", "SOL/USD": "SOL-USD"})
    assert t.venue == "test_venue"
    assert t.to_venue_symbol("BTC/USD") == "BTC-USD"
    assert t.to_canonical("SOL-USD") == "SOL/USD"


def test_create_translator_empty_mapping_raises() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        create_translator("test_venue", {})
