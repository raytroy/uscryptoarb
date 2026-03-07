"""Crypto.com symbol mapping.

Crypto.com Exchange uses underscore-separated uppercase symbols:
    BTC_USD, LTC_BTC, SOL_USD

5 of 8 target pairs are available. USDC pairs (BTC/USDC, LTC/USDC,
SOL/USDC) are not listed on Crypto.com Exchange.
"""

from __future__ import annotations

from uscryptoarb.venues.symbol_translator import SymbolTranslator, create_translator

CRYPTODOTCOM_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "BTC_USD",
    "LTC/USD": "LTC_USD",
    "LTC/BTC": "LTC_BTC",
    "SOL/USD": "SOL_USD",
    "SOL/BTC": "SOL_BTC",
    # BTC/USDC, LTC/USDC, SOL/USDC: not listed on Crypto.com Exchange
}

CRYPTODOTCOM_SYMBOLS: SymbolTranslator = create_translator(
    "cryptodotcom", CRYPTODOTCOM_SYMBOL_MAP
)
