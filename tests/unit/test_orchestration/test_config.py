from __future__ import annotations

from decimal import Decimal

import pytest

from tests.unit.test_orchestration.conftest import FULL_CFG
from uscryptoarb.orchestration.config import (
    _DEFAULT_VENUE_CONFIG,
    LoggingConfig,
    _load_dotenv_if_available,
    load_config,
)

BASIC_CFG = """
venues:
  primary: [kraken]
pairs: [BTC/USD]
arbitrage:
  threshold: '0.1'
  trade_amounts:
    BTC/USD: '1'
fees:
  kraken:
    buy: '0.1'
    sell: '0.1'
"""


def _write_config(tmp_path, text: str):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(text)
    return cfg


# ---------------------------------------------------------------------------
# Smoke test: production config.yaml loads without error.
# No value assertions — just structural validity.
# ---------------------------------------------------------------------------
def test_production_config_loads() -> None:
    cfg = load_config("config.yaml")
    assert cfg.venues
    assert cfg.pairs


# ---------------------------------------------------------------------------
# Parsing logic tests — all use synthetic FULL_CFG via full_config_path
# ---------------------------------------------------------------------------
def test_load_config_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    full_config_path: str,
) -> None:
    monkeypatch.setenv("SMTP_FROM_ADDR", "bot@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    cfg = load_config(full_config_path)
    assert cfg.venues == ("kraken", "coinbase", "gemini", "bitstamp", "okx")
    assert "BTC/USD" in cfg.pairs
    assert cfg.arbitrage.threshold == Decimal("0.0055")
    assert cfg.email.from_addr == "bot@example.com"


def test_decimal_types(full_config_path: str) -> None:
    cfg = load_config(full_config_path)
    assert isinstance(cfg.arbitrage.threshold, Decimal)
    assert all(isinstance(v, Decimal) for v in cfg.arbitrage.trade_amounts.values())


def test_build_fee_schedules_withdrawal_currencies(full_config_path: str) -> None:
    cfg = load_config(full_config_path)
    fs = cfg.fees_by_pair_venue["BTC/USD"]["kraken"]
    assert fs.buy_withdrawal is not None
    assert fs.sell_withdrawal is not None
    assert fs.buy_withdrawal.currency == "BTC"
    assert fs.sell_withdrawal.currency == "USD"


def test_email_config_defaults(
    monkeypatch: pytest.MonkeyPatch,
    full_config_path: str,
) -> None:
    monkeypatch.delenv("SMTP_FROM_ADDR", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    cfg = load_config(full_config_path)
    assert cfg.email.from_addr == ""
    assert cfg.email.password == ""


def test_debug_config_defaults(full_config_path: str) -> None:
    cfg = load_config(full_config_path)
    assert cfg.debug.trace_pairs == ()
    assert cfg.debug.log_level == "INFO"


# ---------------------------------------------------------------------------
# Validation / error tests — use inline YAML via tmp_path (no config.yaml)
# ---------------------------------------------------------------------------
def test_load_config_missing_yaml_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_config("/tmp/does_not_exist.yaml")


def test_load_config_empty_venues_raises(tmp_path) -> None:
    text = """
venues:
  primary: []
pairs: [BTC/USD]
arbitrage:
  threshold: '0.1'
  trade_amounts:
    BTC/USD: '1'
"""
    path = _write_config(tmp_path, text)
    with pytest.raises(ValueError):
        load_config(str(path))


def test_load_config_missing_trade_amount_for_pair_raises(tmp_path) -> None:
    path = _write_config(
        tmp_path,
        BASIC_CFG.replace("BTC/USD: '1'", ""),
    )
    with pytest.raises(ValueError):
        load_config(str(path))


def test_load_config_invalid_pair_format_raises(tmp_path) -> None:
    path = _write_config(
        tmp_path,
        BASIC_CFG.replace("BTC/USD", "BTCUSD"),
    )
    with pytest.raises(ValueError):
        load_config(str(path))


def test_load_config_unknown_venue_raises(tmp_path) -> None:
    path = _write_config(tmp_path, BASIC_CFG.replace("kraken", "bitfinex"))
    with pytest.raises(ValueError):
        load_config(str(path))


def test_venue_config_defaults(tmp_path) -> None:
    path = _write_config(tmp_path, FULL_CFG)
    cfg = load_config(str(path))
    assert cfg.venue_configs["kraken"] == _DEFAULT_VENUE_CONFIG


def test_load_dotenv_falls_back_to_dotenv_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    class DotenvNamespaceModule:
        pass

    class DotenvMainModule:
        @staticmethod
        def load_dotenv() -> None:
            nonlocal called
            called = True

    def fake_import_module(name: str):
        if name == "dotenv":
            return DotenvNamespaceModule()
        if name == "dotenv.main":
            return DotenvMainModule()
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(
        "uscryptoarb.orchestration.config.importlib.import_module",
        fake_import_module,
    )

    _load_dotenv_if_available()
    assert called


def test_logging_config_parsed(full_config_path: str) -> None:
    """Verify logging section is parsed into LoggingConfig."""
    cfg = load_config(full_config_path)
    assert isinstance(cfg.logging, LoggingConfig)
    assert cfg.logging.file_path is None
    assert cfg.logging.max_bytes == 10_485_760
    assert cfg.logging.backup_count == 5
    assert cfg.logging.stats_interval == 20


def test_logging_config_absent_uses_defaults(tmp_path) -> None:
    """If logging section is missing from YAML, defaults are applied."""
    minimal = FULL_CFG.replace(
        "logging:\n"
        "  file_path: null\n"
        "  max_bytes: 10485760\n"
        "  backup_count: 5\n"
        "  stats_interval: 20\n",
        "",
    )
    p2 = tmp_path / "no_logging.yaml"
    p2.write_text(minimal)
    cfg = load_config(str(p2))
    assert cfg.logging.file_path is None
    assert cfg.logging.max_bytes == 10_485_760
    assert cfg.logging.backup_count == 5
    assert cfg.logging.stats_interval == 20


def test_fee_coverage_validation_fails_with_single_venue(tmp_path) -> None:
    cfg_text = FULL_CFG.replace(
        "primary: [kraken, coinbase, gemini, bitstamp, okx]",
        "primary: [kraken]",
    )
    p = tmp_path / "single_venue.yaml"
    p.write_text(cfg_text)
    with pytest.raises(ValueError, match="Insufficient fee coverage"):
        load_config(str(p))
