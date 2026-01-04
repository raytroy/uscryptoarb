from __future__ import annotations

from dataclasses import dataclass
from typing import List

from uscryptoarb.markets.pairs import parse_pair
from uscryptoarb.venues.registry import ohio_eligible


@dataclass(frozen=True, slots=True)
class AppConfig:
    venues: List[str]
    pairs: List[str]


def validate_config(cfg: AppConfig) -> None:
    if not cfg.venues:
        raise ValueError("config.venues must be non-empty")
    if not cfg.pairs:
        raise ValueError("config.pairs must be non-empty")

    # validate venues (and Ohio eligibility)
    _ = ohio_eligible(cfg.venues)

    # validate canonical pairs
    for p in cfg.pairs:
        _ = parse_pair(p)
