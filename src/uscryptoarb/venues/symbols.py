from __future__ import annotations

from dataclasses import dataclass

from uscryptoarb.markets.pairs import CanonicalPair, parse_pair


@dataclass(frozen=True, slots=True)
class SymbolTranslator:
    """
    Maps canonical pairs (BASE/QUOTE) to venue-specific symbols.
    """
    venue: str
    canonical_to_venue: dict[str, str]

    def to_venue_symbol(self, pair: str | CanonicalPair) -> str:
        key = pair.as_str if isinstance(pair, CanonicalPair) else parse_pair(pair).as_str
        try:
            return self.canonical_to_venue[key]
        except KeyError as e:
            raise KeyError(f"{self.venue}: no symbol mapping for {key}") from e
