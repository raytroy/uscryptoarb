from __future__ import annotations

from dataclasses import dataclass, field

from uscryptoarb.markets.pairs import CanonicalPair, parse_pair


@dataclass(frozen=True, slots=True)
class SymbolTranslator:
    """
    Maps canonical pairs (BASE/QUOTE) to venue-specific symbols.
    """

    venue: str
    canonical_to_venue: dict[str, str]
    _venue_to_canonical: dict[str, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        reverse = {venue: canonical for canonical, venue in self.canonical_to_venue.items()}
        object.__setattr__(self, "_venue_to_canonical", reverse)

    def to_venue_symbol(self, pair: str | CanonicalPair) -> str:
        key = pair.as_str if isinstance(pair, CanonicalPair) else parse_pair(pair).as_str
        try:
            return self.canonical_to_venue[key]
        except KeyError as e:
            raise KeyError(f"{self.venue}: no symbol mapping for {key}") from e

    def to_canonical(self, venue_symbol: str) -> str:
        try:
            return self._venue_to_canonical[venue_symbol]
        except KeyError as e:
            raise KeyError(f"{self.venue}: no canonical mapping for {venue_symbol}") from e


def create_translator(venue: str, mapping: dict[str, str]) -> SymbolTranslator:
    """Create a validated SymbolTranslator for a venue.

    Establishes the standard construction pattern for all exchange connectors.
    Use this instead of constructing SymbolTranslator directly.

    Args:
        venue: Venue identifier (e.g. "kraken", "coinbase").
        mapping: Canonical pair → venue symbol mapping. Must be non-empty.

    Returns:
        Configured SymbolTranslator with forward and reverse lookups.

    Raises:
        ValueError: If mapping is empty.
    """
    if not mapping:
        raise ValueError(f"Symbol mapping for {venue} must be non-empty")
    return SymbolTranslator(venue=venue, canonical_to_venue=mapping)
