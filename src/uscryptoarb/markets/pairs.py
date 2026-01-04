from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CanonicalPair:
    base: str
    quote: str

    @property
    def as_str(self) -> str:
        return f"{self.base}/{self.quote}"


def parse_pair(s: str) -> CanonicalPair:
    """
    Parse canonical pair strings like 'SOL/USDC'.
    """
    if not s or "/" not in s:
        raise ValueError("pair must look like BASE/QUOTE")
    base, quote = s.split("/", 1)
    base = base.strip().upper()
    quote = quote.strip().upper()
    if not base or not quote:
        raise ValueError("pair must look like BASE/QUOTE")
    return CanonicalPair(base=base, quote=quote)
