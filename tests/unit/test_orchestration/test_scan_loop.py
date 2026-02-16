from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from dataclasses import replace
from decimal import Decimal

import pytest

from uscryptoarb.connectors.connector_base import ExchangeConnector
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.orchestration.config import load_config
from uscryptoarb.orchestration.scan_loop import (
    create_connectors,
    fetch_all_venues,
    reorganize_by_pair,
    run_scan_cycle,
    run_scan_loop,
)


class MockConnector(ExchangeConnector):
    def __init__(self, venue: str, tobs_or_exc):
        self._venue = venue
        self._value = tobs_or_exc

    @property
    def venue(self) -> str:
        return self._venue

    async def fetch_tickers(self, pairs: list[str]) -> dict[str, TopOfBook]:
        if isinstance(self._value, Exception):
            raise self._value
        tobs: dict[str, TopOfBook] = self._value
        return {p: tob for p, tob in tobs.items() if p in pairs}


def _tob(venue: str, pair: str, bid: str, ask: str) -> TopOfBook:
    return TopOfBook(
        venue=venue,
        pair=pair,
        ts_local_ms=1707900000000,
        ts_exchange_ms=None,
        bid_px=Decimal(bid),
        bid_sz=Decimal("1"),
        ask_px=Decimal(ask),
        ask_sz=Decimal("1"),
    )


def test_create_connectors_all_venues(full_config_path: str) -> None:
    config = load_config(full_config_path)

    async def run() -> None:
        async with AsyncExitStack() as stack:
            connectors = await create_connectors(config, stack)
            assert "kraken" in connectors
            assert "coinbase" in connectors
            assert "gemini" in connectors

    asyncio.run(run())


def test_fetch_all_venues_one_fails() -> None:
    connectors = {
        "kraken": MockConnector("kraken", {"BTC/USD": _tob("kraken", "BTC/USD", "101", "102")}),
        "coinbase": MockConnector("coinbase", RuntimeError("boom")),
    }

    async def run() -> None:
        out, venue_errors = await fetch_all_venues(connectors, ["BTC/USD"], "run1")
        assert list(out) == ["kraken"]
        assert venue_errors == {"coinbase": 1}

    asyncio.run(run())


def test_fetch_all_venues_success_no_errors() -> None:
    connectors = {
        "kraken": MockConnector("kraken", {"BTC/USD": _tob("kraken", "BTC/USD", "101", "102")}),
        "coinbase": MockConnector(
            "coinbase",
            {"BTC/USD": _tob("coinbase", "BTC/USD", "103", "104")},
        ),
    }

    async def run() -> None:
        out, venue_errors = await fetch_all_venues(connectors, ["BTC/USD"], "run_ok")
        assert set(out.keys()) == {"kraken", "coinbase"}
        assert venue_errors == {}

    asyncio.run(run())


def test_reorganize_by_pair_basic() -> None:
    venue_data = {
        "kraken": {"BTC/USD": _tob("kraken", "BTC/USD", "101", "102")},
        "coinbase": {"BTC/USD": _tob("coinbase", "BTC/USD", "103", "104")},
    }
    out = reorganize_by_pair(venue_data, ["BTC/USD"])
    assert set(out["BTC/USD"].keys()) == {"kraken", "coinbase"}


def test_run_scan_cycle_detects_opportunity(full_config_path: str) -> None:
    base_cfg = load_config(full_config_path)
    arb = replace(base_cfg.arbitrage, max_staleness_ms=10_000_000_000_000)
    cfg = replace(base_cfg, pairs=("BTC/USD",), arbitrage=arb)
    connectors = {
        "kraken": MockConnector("kraken", {"BTC/USD": _tob("kraken", "BTC/USD", "109", "110")}),
        "coinbase": MockConnector(
            "coinbase",
            {"BTC/USD": _tob("coinbase", "BTC/USD", "130", "131")},
        ),
    }

    async def run() -> None:
        opps, _errors = await run_scan_cycle(connectors, cfg, "run2")
        assert len(opps) >= 1

    asyncio.run(run())


def test_run_scan_cycle_missing_fees_skips(full_config_path: str) -> None:
    cfg = replace(load_config(full_config_path), pairs=("BTC/USD",), fees_by_pair_venue={})
    connectors = {
        "kraken": MockConnector("kraken", {"BTC/USD": _tob("kraken", "BTC/USD", "109", "110")}),
        "coinbase": MockConnector(
            "coinbase",
            {"BTC/USD": _tob("coinbase", "BTC/USD", "130", "131")},
        ),
    }

    async def run() -> None:
        opps, _errors = await run_scan_cycle(connectors, cfg, "run3")
        assert opps == []

    asyncio.run(run())


def test_run_scan_loop_single_cycle_and_shutdown(full_config_path: str) -> None:
    cfg = load_config(full_config_path)
    shutdown = asyncio.Event()

    async def run() -> None:
        async def stop_soon() -> None:
            await asyncio.sleep(0.2)
            shutdown.set()

        stopper = asyncio.create_task(stop_soon())
        cfg2 = replace(cfg, polling=replace(cfg.polling, interval_seconds=1))
        stats = await run_scan_loop(cfg2, shutdown, stats_interval=0)
        assert stats.cycles_completed >= 1
        await stopper

    asyncio.run(run())


def test_run_scan_loop_logs_stats_at_interval(
    full_config_path: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify [stats] summary is logged at the configured interval."""
    cfg = load_config(full_config_path)
    shutdown = asyncio.Event()

    async def run() -> None:
        async def stop_after_delay() -> None:
            await asyncio.sleep(0.5)
            shutdown.set()

        stopper = asyncio.create_task(stop_after_delay())
        cfg2 = replace(cfg, polling=replace(cfg.polling, interval_seconds=1))
        with caplog.at_level(logging.INFO):
            stats = await run_scan_loop(cfg2, shutdown, stats_interval=1)
        stats_lines = [r for r in caplog.records if "[stats]" in r.message]
        assert len(stats_lines) >= 2
        assert "Final:" in stats_lines[-1].message
        assert stats.cycles_completed >= 1
        await stopper

    asyncio.run(run())


class TestLogPairSpreads:
    """Tests for _log_pair_spreads diagnostic logging."""

    def test_logs_spread_for_two_venues(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify spread logging outputs pair, venues, and spread percentage."""
        from uscryptoarb.orchestration.scan_loop import _log_pair_spreads

        tobs = {
            "kraken": _tob("kraken", "BTC/USD", "97100", "97200"),
            "coinbase": _tob("coinbase", "BTC/USD", "97300", "97400"),
        }
        with caplog.at_level(logging.INFO):
            _log_pair_spreads("BTC/USD", tobs, Decimal("0.0055"), "test1")

        assert len(caplog.records) == 1
        msg = caplog.records[0].message
        assert "BTC/USD" in msg
        assert "kraken" in msg
        assert "coinbase" in msg
        assert "best_spread=" in msg
        assert "threshold=0.550%" in msg

    def test_spread_sign_positive_when_arb_exists(self, caplog: pytest.LogCaptureFixture) -> None:
        """Positive spread when sell bid > buy ask (arb direction)."""
        from uscryptoarb.orchestration.scan_loop import _log_pair_spreads

        tobs = {
            "kraken": _tob("kraken", "BTC/USD", "97100", "97200"),
            "coinbase": _tob("coinbase", "BTC/USD", "97300", "97400"),
        }
        with caplog.at_level(logging.INFO):
            _log_pair_spreads("BTC/USD", tobs, Decimal("0.0055"), "test2")

        assert "+0.103%" in caplog.records[0].message

    def test_spread_sign_negative_when_no_arb(self, caplog: pytest.LogCaptureFixture) -> None:
        """Negative spread when best bid < best ask (no arb)."""
        from uscryptoarb.orchestration.scan_loop import _log_pair_spreads

        tobs = {
            "kraken": _tob("kraken", "BTC/USD", "97100", "97200"),
            "coinbase": _tob("coinbase", "BTC/USD", "97100", "97200"),
        }
        with caplog.at_level(logging.INFO):
            _log_pair_spreads("BTC/USD", tobs, Decimal("0.0055"), "test3")

        assert "best_spread=-" in caplog.records[0].message

    def test_venues_sorted_alphabetically(self, caplog: pytest.LogCaptureFixture) -> None:
        """Venue order in log is alphabetical for deterministic output."""
        from uscryptoarb.orchestration.scan_loop import _log_pair_spreads

        tobs = {
            "zebra_exchange": _tob("zebra_exchange", "BTC/USD", "97100", "97200"),
            "alpha_exchange": _tob("alpha_exchange", "BTC/USD", "97100", "97200"),
        }
        with caplog.at_level(logging.INFO):
            _log_pair_spreads("BTC/USD", tobs, Decimal("0.0055"), "test4")

        msg = caplog.records[0].message
        alpha_pos = msg.index("alpha_exchange")
        zebra_pos = msg.index("zebra_exchange")
        assert alpha_pos < zebra_pos
