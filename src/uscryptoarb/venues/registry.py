from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True, slots=True)
class VenueInfo:
    venue: str
    ohio_allowed: bool


# Start tiny. We’ll expand over time.
DEFAULT_VENUES: Dict[str, VenueInfo] = {
    "kraken": VenueInfo(venue="kraken", ohio_allowed=True),
    "coinbase": VenueInfo(venue="coinbase", ohio_allowed=True),
    "gemini": VenueInfo(venue="gemini", ohio_allowed=True),
}


def ohio_eligible(venues: Iterable[str]) -> List[str]:
    out: List[str] = []
    for v in venues:
        key = v.strip().lower()
        info = DEFAULT_VENUES.get(key)
        if info is None:
            raise ValueError(f"unknown venue: {v}")
        if not info.ohio_allowed:
            raise ValueError(f"venue not ohio-eligible: {v}")
        out.append(key)
    return out
