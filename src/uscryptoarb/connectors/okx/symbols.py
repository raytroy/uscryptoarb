"""OKX US symbol mapping.

OKX uses dash-separated uppercase symbols: BTC-USD (same format as Coinbase).
Explicit map per LL-001 — verify, don't generate.

Available: 7/8 target pairs. LTC/BTC is NOT listed on OKX US (verified
via notebooks/04_okx_exploration.ipynb Section 2, 2026-02-16).
"""

from __future__ import annotations

from uscryptoarb.venues.symbol_translator import create_translator

OKX_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "BTC-USD",
    "BTC/USDC": "BTC-USDC",
    "LTC/USD": "LTC-USD",
    "LTC/USDC": "LTC-USDC",
    "SOL/USD": "SOL-USD",
    "SOL/USDC": "SOL-USDC",
    "SOL/BTC": "SOL-BTC",
}

OKX_SYMBOLS = create_translator("okx", OKX_SYMBOL_MAP)
