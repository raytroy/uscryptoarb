"""CEX.IO symbol mapping.

CEX.IO uses slash-separated uppercase symbols in URL path segments:
    /api/order_book/BTC/USD

Our canonical format happens to match (BTC/USD), but the connector must
split on "/" to build the URL path. The SymbolTranslator handles the
canonical ↔ venue mapping; the client handles URL construction.

All 8 canonical pairs are mapped. Pairs that CEX.IO does not support
(BTC/USDC, SOL/BTC) or that have empty order books (LTC/USDC, LTC/BTC)
are handled gracefully by _fetch_tickers_per_pair error logging.
"""

from __future__ import annotations

from uscryptoarb.venues.symbol_translator import SymbolTranslator, create_translator

CEXIO_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "BTC/USD",
    "BTC/USDC": "BTC/USDC",
    "LTC/USD": "LTC/USD",
    "LTC/USDC": "LTC/USDC",
    "LTC/BTC": "LTC/BTC",
    "SOL/USD": "SOL/USD",
    "SOL/USDC": "SOL/USDC",
    "SOL/BTC": "SOL/BTC",
}

CEXIO_SYMBOLS: SymbolTranslator = create_translator("cexio", CEXIO_SYMBOL_MAP)
