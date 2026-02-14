import pytest

from uscryptoarb.connectors.coinbase.symbols import (
    COINBASE_SYMBOL_MAP,
    COINBASE_SYMBOLS,
    supported_pairs,
)


def test_all_pairs_forward_lookup() -> None:
    for canonical, venue_symbol in COINBASE_SYMBOL_MAP.items():
        assert COINBASE_SYMBOLS.to_venue_symbol(canonical) == venue_symbol


def test_all_pairs_reverse_lookup() -> None:
    for canonical, venue_symbol in COINBASE_SYMBOL_MAP.items():
        assert COINBASE_SYMBOLS.to_canonical(venue_symbol) == canonical


def test_unknown_pair_raises() -> None:
    with pytest.raises(KeyError):
        COINBASE_SYMBOLS.to_venue_symbol("ETH/USD")


def test_supported_pairs_returns_eight() -> None:
    pairs = supported_pairs()
    assert len(pairs) == 8
    assert set(pairs) == set(COINBASE_SYMBOL_MAP)


def test_unknown_symbol_reverse_raises() -> None:
    with pytest.raises(KeyError):
        COINBASE_SYMBOLS.to_canonical("UNKNOWN")
