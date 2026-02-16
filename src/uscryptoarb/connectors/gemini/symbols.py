from __future__ import annotations

from uscryptoarb.venues.symbols import create_translator

GEMINI_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "btcusd",
    "BTC/USDC": "btcusdc",
    "LTC/USD": "ltcusd",
    "LTC/USDC": "ltcusdc",
    "LTC/BTC": "ltcbtc",
    "SOL/USD": "solusd",
    "SOL/USDC": "solusdc",
    "SOL/BTC": "solbtc",
}

GEMINI_SYMBOLS = create_translator("gemini", GEMINI_SYMBOL_MAP)


def supported_pairs() -> list[str]:
    return list(GEMINI_SYMBOL_MAP)
