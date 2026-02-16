from __future__ import annotations

import pytest

from uscryptoarb.connectors.okx.symbols import OKX_SYMBOL_MAP, OKX_SYMBOLS


def test_forward_lookup_all_pairs() -> None:
    for canonical, venue in OKX_SYMBOL_MAP.items():
        assert OKX_SYMBOLS.to_venue_symbol(canonical) == venue


def test_reverse_lookup_all_pairs() -> None:
    for canonical, venue in OKX_SYMBOL_MAP.items():
        assert OKX_SYMBOLS.to_canonical(venue) == canonical


def test_unknown_canonical_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        OKX_SYMBOLS.to_venue_symbol("DOGE/USD")


def test_symbol_map_has_exactly_seven_entries() -> None:
    assert len(OKX_SYMBOL_MAP) == 7


def test_ltc_btc_deliberately_absent() -> None:
    with pytest.raises(KeyError):
        OKX_SYMBOLS.to_venue_symbol("LTC/BTC")


def test_unknown_venue_symbol_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        OKX_SYMBOLS.to_canonical("DOGE-USD")


def test_venue_name_is_okx() -> None:
    assert OKX_SYMBOLS.venue == "okx"


def test_round_trip_all_pairs() -> None:
    for canonical in OKX_SYMBOL_MAP:
        venue = OKX_SYMBOLS.to_venue_symbol(canonical)
        assert OKX_SYMBOLS.to_canonical(venue) == canonical
