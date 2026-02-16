from __future__ import annotations

from uscryptoarb.venues.symbol_translator import create_translator

KRAKEN_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "XXBTZUSD",
    "BTC/USDC": "XBTUSDC",
    "LTC/USD": "XLTCZUSD",
    "LTC/USDC": "LTCUSDC",
    "LTC/BTC": "XLTCXXBT",
    "SOL/USD": "SOLUSD",
    "SOL/USDC": "SOLUSDC",
    "SOL/BTC": "SOLXBT",
}

KRAKEN_SYMBOLS = create_translator("kraken", KRAKEN_SYMBOL_MAP)


def supported_pairs() -> list[str]:
    return list(KRAKEN_SYMBOL_MAP)
