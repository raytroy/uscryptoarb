from __future__ import annotations

from uscryptoarb.venues.symbols import SymbolTranslator

COINBASE_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "BTC-USD",
    "BTC/USDC": "BTC-USDC",
    "LTC/USD": "LTC-USD",
    "LTC/USDC": "LTC-USDC",
    "LTC/BTC": "LTC-BTC",
    "SOL/USD": "SOL-USD",
    "SOL/USDC": "SOL-USDC",
    "SOL/BTC": "SOL-BTC",
}

COINBASE_SYMBOLS = SymbolTranslator(
    venue="coinbase",
    canonical_to_venue=COINBASE_SYMBOL_MAP,
)


def supported_pairs() -> list[str]:
    return list(COINBASE_SYMBOL_MAP)
