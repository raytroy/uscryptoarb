# USCryptoArb

Cross-exchange, taker-only crypto arbitrage scanner for Ohio-eligible exchanges.

## Status

**Phase 1: Detection** — Building exchange connectors and arbitrage detection pipeline.

## Exchanges

| Exchange | Status | Pairs |
|----------|--------|-------|
| Kraken | ✅ Connector built | BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC |
| Coinbase | 🔲 Planned | — |
| Gemini | 🔲 Planned | — |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
ruff check src/ tests/
mypy src/
pytest tests/ -v
```

## Architecture

See [PROJECT_INSTRUCTIONS.md](PROJECT_INSTRUCTIONS.md) for full documentation.
