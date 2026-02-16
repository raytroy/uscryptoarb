"""Orchestration test fixtures.

Provides a self-contained synthetic config.yaml so that unit tests
never depend on values in the production config.yaml.  A single smoke
test (test_production_config_loads) validates that the real file parses
without error, but no test asserts specific production values.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Synthetic config — all values are known constants controlled by tests.
# Includes every section that load_config() expects so it can be used as a
# drop-in replacement for the real config.yaml in any orchestration test.
# ---------------------------------------------------------------------------
FULL_CFG = """\
venues:
  primary: [kraken, coinbase, gemini]

pairs:
  - BTC/USD
  - LTC/USD

arbitrage:
  threshold: "0.0055"
  min_bankroll_limit: "0.10"
  max_staleness_ms: 5000
  trade_amounts:
    BTC/USD: "0.01"
    LTC/USD: "1.0"

polling:
  interval_seconds: 5
  max_concurrent_requests: 10

venue_configs:
  kraken:
    rate_limit_ms: 500
    timeout_s: 10.0
    max_retries: 3
  coinbase:
    rate_limit_ms: 150
    timeout_s: 10.0
    max_retries: 3
  gemini:
    rate_limit_ms: 200
    timeout_s: 10.0
    max_retries: 3

fees:
  kraken:
    buy: "0.0026"
    sell: "0.0026"
  coinbase:
    buy: "0.006"
    sell: "0.006"
  gemini:
    buy: "0.004"
    sell: "0.004"

notifications:
  email:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587
    recipients: []

debug:
  enabled: false
  trace_pairs: []
  log_level: INFO
"""


@pytest.fixture()
def full_config_path(tmp_path):
    """Write a complete synthetic config.yaml and return its path as str."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(FULL_CFG)
    return str(cfg)
