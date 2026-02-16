# Test Fixtures

This directory stores deterministic fixture data used by tests.

## Provenance

### fee_schedules.json

- **Source**: Manually compiled from exchange documentation (2025)
- **Created**: 2026-02-14
- **Purpose**: Deterministic fee/accuracy data for calculation layer tests
- **Contents**: Trading fees (flat rates per DEC-013), withdrawal fees, and trading accuracy (precision/min/max) for Kraken, Coinbase, Gemini across all 8 target pairs
- **Notes**: Withdrawal fees are conservative estimates. Kraken fees are dynamic and may drift from these values. Coinbase and Gemini withdrawal fees are set to zero (free withdrawals). Trading accuracy data sourced from Kraken AssetPairs API, Coinbase Products API, and Gemini /v1/symbols/details/{symbol} API responses (captured in exploration notebooks and via direct API calls 2026-02-16).


### gemini_book_btc_usd.json
- **Contains**: Gemini /v1/book/btcusd response with limit_bids=1&limit_asks=1. Standard USD pair.
- **Source**: Live capture from Gemini public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-15
- **Used by**: `tests/unit/test_connectors/test_gemini/test_parser.py`
- **Notes**: All fields are strings. Timestamp is Unix seconds as integer string (not ms, not ISO 8601). Field name is "amount" (not "size" like Coinbase). No wrapper object — bids/asks are top-level keys.

### gemini_book_ltc_btc.json
- **Contains**: Gemini /v1/book/ltcbtc response. BTC-quoted pair with 7-decimal-place prices.
- **Source**: Live capture from Gemini public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-15
- **Used by**: `tests/unit/test_connectors/test_gemini/test_parser.py`
- **Notes**: Tests parser handles high-precision BTC-quoted prices correctly (bid=0.0007979, ask=0.0007988).

### gemini_book_sol_btc.json
- **Contains**: Gemini /v1/book/solbtc response. BTC-quoted pair with 7-decimal-place prices.
- **Source**: Live capture from Gemini public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-15
- **Used by**: `tests/unit/test_connectors/test_gemini/test_parser.py`
- **Notes**: Tests parser handles 7-decimal-place prices for SOL/BTC (bid=0.0012499, ask=0.0012506).
