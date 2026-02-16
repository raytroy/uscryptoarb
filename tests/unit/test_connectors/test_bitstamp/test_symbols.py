import pytest

from uscryptoarb.connectors.bitstamp.symbols import (
    BITSTAMP_SYMBOL_MAP,
    BITSTAMP_SYMBOLS,
)


def test_forward_lookup_all_pairs() -> None:
    for canonical, expected in BITSTAMP_SYMBOL_MAP.items():
        assert BITSTAMP_SYMBOLS.to_venue_symbol(canonical) == expected


def test_reverse_lookup_all_pairs() -> None:
    for canonical, venue_sym in BITSTAMP_SYMBOL_MAP.items():
        assert BITSTAMP_SYMBOLS.to_canonical(venue_sym) == canonical


def test_unknown_pair_raises() -> None:
    with pytest.raises(KeyError, match="bitstamp"):
        BITSTAMP_SYMBOLS.to_venue_symbol("ETH/USD")


def test_symbol_map_has_six_pairs() -> None:
    """Bitstamp supports 6/8 target pairs (missing LTC/USDC, SOL/BTC)."""
    assert len(BITSTAMP_SYMBOL_MAP) == 6


def test_unknown_venue_symbol_raises() -> None:
    with pytest.raises(KeyError, match="bitstamp"):
        BITSTAMP_SYMBOLS.to_canonical("fakepair")


def test_missing_ltc_usdc_raises() -> None:
    """LTC/USDC is not available on Bitstamp."""
    with pytest.raises(KeyError):
        BITSTAMP_SYMBOLS.to_venue_symbol("LTC/USDC")


def test_missing_sol_btc_raises() -> None:
    """SOL/BTC is not available on Bitstamp."""
    with pytest.raises(KeyError):
        BITSTAMP_SYMBOLS.to_venue_symbol("SOL/BTC")


def test_usd_not_equal_usdc() -> None:
    """USD and USDC map to different symbols (DEC-001)."""
    assert BITSTAMP_SYMBOLS.to_venue_symbol("BTC/USD") != BITSTAMP_SYMBOLS.to_venue_symbol(
        "BTC/USDC"
    )
