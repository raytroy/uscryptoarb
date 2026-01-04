import pytest

from uscryptoarb.config.app_config import AppConfig, validate_config
from uscryptoarb.venues.registry import ohio_eligible


def test_ohio_eligible_ok() -> None:
    assert ohio_eligible(["Kraken", "coinbase"]) == ["kraken", "coinbase"]


def test_ohio_eligible_unknown_rejected() -> None:
    with pytest.raises(ValueError):
        ohio_eligible(["notarealexchange"])


def test_config_validation_ok() -> None:
    cfg = AppConfig(
        venues=["kraken"],
        pairs=["BTC/USD", "SOL/USDC"],
    )
    validate_config(cfg)


def test_config_validation_bad_pair_rejected() -> None:
    cfg = AppConfig(venues=["kraken"], pairs=["BTCUSD"])
    with pytest.raises(ValueError):
        validate_config(cfg)
