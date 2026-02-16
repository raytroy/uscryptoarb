from __future__ import annotations

from uscryptoarb.venues.symbol_translator import create_translator

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

COINBASE_SYMBOLS = create_translator("coinbase", COINBASE_SYMBOL_MAP)

