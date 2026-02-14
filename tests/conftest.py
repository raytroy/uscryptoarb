import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def kraken_ticker_fixture() -> dict:
    with open(FIXTURES_DIR / "kraken_ticker_response.json") as f:
        return json.load(f)


@pytest.fixture
def kraken_orderbook_fixture() -> dict:
    with open(FIXTURES_DIR / "kraken_orderbook_response.json") as f:
        return json.load(f)


@pytest.fixture
def kraken_asset_pairs_fixture() -> dict:
    with open(FIXTURES_DIR / "kraken_asset_pairs_btcusd.json") as f:
        return json.load(f)


@pytest.fixture
def coinbase_product_book_btc_usd_fixture() -> dict:
    with open(FIXTURES_DIR / "coinbase_product_book_btc_usd.json") as f:
        return json.load(f)


@pytest.fixture
def coinbase_product_book_ltc_btc_fixture() -> dict:
    with open(FIXTURES_DIR / "coinbase_product_book_ltc_btc.json") as f:
        return json.load(f)


@pytest.fixture
def coinbase_product_book_sol_btc_fixture() -> dict:
    with open(FIXTURES_DIR / "coinbase_product_book_sol_btc.json") as f:
        return json.load(f)
