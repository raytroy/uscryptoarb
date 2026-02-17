# USCryptoArb

Cross-exchange, taker-only crypto arbitrage scanner for Ohio-eligible exchanges.

## Documentation

| Document | Purpose |
|----------|---------|
| [PROJECT_INSTRUCTIONS.md](PROJECT_INSTRUCTIONS.md) | Full specifications and coding standards |
| [CLAUDE_INSTRUCTIONS.md](CLAUDE_INSTRUCTIONS.md) | Condensed AI assistant instructions |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [docs/LESSONS_LEARNED.md](docs/LESSONS_LEARNED.md) | Mistake prevention database |
| [docs/SESSION_HANDOFFS.md](docs/SESSION_HANDOFFS.md) | Multi-session continuity log |
| [docs/DECISION_LOG.md](docs/DECISION_LOG.md) | Architectural decision records |
| [docs/MATHEMATICA_MAP.md](docs/MATHEMATICA_MAP.md) | Mathematica → Python porting tracker |

## Status

**Phase 1: Detection** — Building exchange connectors and arbitrage detection pipeline.

## Exchanges

| Exchange | Status | Pairs |
|----------|--------|-------|
| Kraken | ✅ Connector built | BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC |
| Coinbase | ✅ Connector built | BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC |
| Gemini | ✅ Connector built | BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC |
| Bitstamp | ✅ Connector built | 6/8 pairs (missing LTC/USDC, SOL/BTC) |
| OKX | ✅ Connector built | 7/8 pairs (missing LTC/BTC) |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```


## Usage

### Quick Start

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your SMTP credentials (optional for email alerts)

# Run the scanner
python -m uscryptoarb

# Dry run (single scan, no email)
python -m uscryptoarb --dry-run

# Debug a specific pair
python -m uscryptoarb --trace-pair BTC/USD --log-level DEBUG
```

### Configuration

See `config.yaml` for all settings. Sensitive values (passwords, API keys) go in `.env`.

## Tests

```bash
ruff check src/ tests/
mypy src/
pytest tests/ -v
```

## Architecture

See [PROJECT_INSTRUCTIONS.md](PROJECT_INSTRUCTIONS.md) for full documentation.
