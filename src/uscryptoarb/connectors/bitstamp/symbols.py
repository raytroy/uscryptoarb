from __future__ import annotations

from uscryptoarb.venues.symbol_translator import create_translator

# Only 6/8 target pairs available on Bitstamp.
# Missing: LTC/USDC (ltcusdc not listed), SOL/BTC (solbtc not listed).
# Verified via /api/v2/trading-pairs-info/ — notebook Section 2.
# These pairs are NOT removed from config.yaml (other exchanges support them).
# The connector will log a warning and skip them at runtime.
BITSTAMP_SYMBOL_MAP: dict[str, str] = {
    "BTC/USD": "btcusd",
    "BTC/USDC": "btcusdc",
    "LTC/USD": "ltcusd",
    "LTC/BTC": "ltcbtc",
    "SOL/USD": "solusd",
    "SOL/USDC": "solusdc",
}

BITSTAMP_SYMBOLS = create_translator("bitstamp", BITSTAMP_SYMBOL_MAP)
