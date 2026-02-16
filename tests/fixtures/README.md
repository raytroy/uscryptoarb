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

### bitstamp_book_btc_usd.json
- **Contains**: Bitstamp order book response for BTC/USD. Arrays-of-arrays format (LL-070), integer prices, microtimestamp precision (LL-071).
- **Source**: Live capture from Bitstamp public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_bitstamp/test_parser.py`
- **Notes**: BTC/USD has counter_decimals=0 (integer prices). Tests parser handles arrays-of-arrays format correctly.

### bitstamp_book_ltc_btc.json
- **Contains**: Bitstamp order book response for LTC/BTC. BTC-quoted pair with 8-decimal-place prices.
- **Source**: Live capture from Bitstamp public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_bitstamp/test_parser.py`
- **Notes**: Tests parser handles high-precision BTC-quoted prices (0.00080295).

### bitstamp_book_btc_usdc.json
- **Contains**: Bitstamp order book response for BTC/USDC. Verifies USD ≠ USDC (DEC-001).
- **Source**: Live capture from Bitstamp public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_bitstamp/test_parser.py`
- **Notes**: Tests parser handles USDC-quoted pair distinctly from USD pair.

## Integration Test Data

The integration tests in `tests/integration/test_end_to_end.py` use **inline synthetic
response data** rather than fixture files. This is intentional:

- Integration test fixtures encode specific price relationships (e.g., "Kraken ask is 2.4%
  below Coinbase bid") that would be confusing in generic fixture files.
- Each test scenario needs precisely controlled prices to deterministically trigger
  (or not trigger) the 0.55% threshold.
- Keeping response data inline makes the price arithmetic visible next to the assertions.

No fixture JSON files were created for integration tests.

### okx_ticker_btc_usd.json
- **Contains**: OKX /api/v5/market/ticker response for BTC-USD (full envelope with code/msg/data). Standard USD pair.
- **Source**: Live capture from OKX US V5 public API during notebook exploration (Section 11)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_okx/test_parser.py`
- **Notes**: All prices/sizes are strings. Timestamp (`ts`) is Unix milliseconds as string — NOT seconds (LL-071). Response includes full OKX envelope with `code`, `msg`, `data` fields. `data` is a single-element array.

### okx_ticker_sol_btc.json
- **Contains**: OKX ticker response for SOL-BTC. Crypto-cross pair with 7-decimal-place prices.
- **Source**: Constructed from live data captured in notebook exploration (Section 3)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_okx/test_parser.py`
- **Notes**: Tests parser handles high-precision BTC-quoted prices correctly (bidPx=0.0012513, askPx=0.0012516).

### okx_error_invalid_instrument.json
- **Contains**: OKX error response for invalid instrument query. HTTP 200 with non-zero code (LL-070).
- **Source**: Live capture from OKX US V5 API with `instId=FAKE-PAIR` (notebook Section 11)
- **Date captured**: 2026-02-16
- **Used by**: `tests/unit/test_connectors/test_okx/test_parser.py`
- **Notes**: Demonstrates OKX's HTTP-200-for-errors pattern. `code: "51001"`, empty `data` array.
