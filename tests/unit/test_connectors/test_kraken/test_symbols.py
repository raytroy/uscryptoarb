import pytest

from uscryptoarb.connectors.kraken.symbols import KRAKEN_SYMBOL_MAP, KRAKEN_SYMBOLS, supported_pairs


def test_all_pairs_forward_lookup() -> None:
    for canonical, venue_symbol in KRAKEN_SYMBOL_MAP.items():
        assert KRAKEN_SYMBOLS.to_venue_symbol(canonical) == venue_symbol


def test_all_pairs_reverse_lookup() -> None:
    for canonical, venue_symbol in KRAKEN_SYMBOL_MAP.items():
        assert KRAKEN_SYMBOLS.to_canonical(venue_symbol) == canonical


def test_unknown_pair_raises() -> None:
    with pytest.raises(KeyError):
        KRAKEN_SYMBOLS.to_venue_symbol("ETH/USD")


def test_supported_pairs_returns_eight() -> None:
    pairs = supported_pairs()
    assert len(pairs) == 8
    assert set(pairs) == set(KRAKEN_SYMBOL_MAP)


def test_unknown_symbol_reverse_raises() -> None:
    with pytest.raises(KeyError):
        KRAKEN_SYMBOLS.to_canonical("UNKNOWN")
