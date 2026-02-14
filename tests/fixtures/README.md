# Test Fixtures

This directory stores deterministic fixture data used by tests.

## Provenance

### fee_schedules.json

- **Source**: Manually compiled from exchange documentation (2025)
- **Created**: 2026-02-14
- **Purpose**: Deterministic fee/accuracy data for calculation layer tests
- **Contents**: Trading fees (flat rates per DEC-013), withdrawal fees, and trading accuracy (precision/min/max) for Kraken, Coinbase, Gemini across all 8 target pairs
- **Notes**: Withdrawal fees are conservative estimates. Kraken fees are dynamic and may drift from these values. Coinbase and Gemini withdrawal fees are set to zero (free withdrawals). Trading accuracy data sourced from Kraken AssetPairs API and Coinbase Products API responses captured in exploration notebooks.
