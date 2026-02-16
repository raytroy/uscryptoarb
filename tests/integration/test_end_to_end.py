"""End-to-end integration tests for the Phase 1 detection pipeline.

Tests the full data flow with mocked HTTP responses:
    Mocked HTTP → connector parsing → TopOfBook → calculation → strategy → notification

These tests exercise run_scan_cycle() — the orchestration function that wires
all layers together. Unlike unit tests that mock at the connector level, these
mock at the HTTP transport layer (httpx.MockTransport) so that connector parsing,
symbol translation, and response validation are all tested as part of the flow.

Does NOT test:
    - create_connectors() (tested in test_scan_loop.py)
    - run_scan_loop() infinite loop (manual testing only)
    - Real network I/O (that's manual validation)

Design decisions:
    - Connectors built manually with MockTransport (bypasses create_connectors)
    - Config built via load_config(synthetic_yaml) (exercises real config parsing)
    - now_ms() patched in all 3 import sites for deterministic timestamps
    - Inline synthetic response data (not fixture files) for controlled price arithmetic
    - BackoffPolicy(1ms) + max_retries=1 for fast failure in degradation tests
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from decimal import Decimal
from functools import wraps
from pathlib import Path
from unittest.mock import patch

import httpx

from uscryptoarb.calculation.calc_types import ArbOpportunity
from uscryptoarb.connectors.coinbase.client import CoinbaseClient
from uscryptoarb.connectors.gemini.client import GeminiClient
from uscryptoarb.connectors.kraken.client import KrakenClient
from uscryptoarb.http.backoff import BackoffPolicy
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.notification.email import EmailConfig, format_opportunity_email, send_alert
from uscryptoarb.orchestration.config import load_config
from uscryptoarb.orchestration.scan_loop import run_scan_cycle

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXED_TS_MS = 1707900000000  # Deterministic timestamp for all now_ms() patches

FAST_BACKOFF = BackoffPolicy(base_ms=1, cap_ms=1, jitter_ratio=0)

# Synthetic config YAML — integration-test-specific values.
# Uses real fee_schedules.json (loaded by load_config from importlib.resources)
# so fee math exercises the real production fee structures.
INTEGRATION_CFG_TEMPLATE = """\
venues:
  primary: [{venues}]

pairs:
  - BTC/USD

arbitrage:
  threshold: "0.0055"
  min_bankroll_limit: "0.10"
  max_staleness_ms: 10000000000000
  trade_amounts:
    BTC/USD: "0.01"

polling:
  interval_seconds: 5
  max_concurrent_requests: 10

venue_configs:
{venue_configs}

fees:
{fees}

notifications:
  email:
    enabled: {email_enabled}
    smtp_host: smtp.gmail.com
    smtp_port: 587
    recipients: {recipients}

debug:
  enabled: false
  trace_pairs: []
  log_level: INFO
"""

_VENUE_CONFIG_BLOCK = """\
  {venue}:
    rate_limit_ms: 0
    timeout_s: 5.0
    max_retries: 1"""

_FEE_BLOCK = """\
  {venue}:
    buy: "0.0026"
    sell: "0.0026"
"""


# ---------------------------------------------------------------------------
# Synthetic HTTP Response Builders
# ---------------------------------------------------------------------------


def _kraken_ticker_response(bid: str, ask: str) -> dict:
    """Build a minimal valid Kraken ticker response for BTC/USD (XXBTZUSD).

    Kraken ticker format: a=[ask_price, whole_lot_volume, lot_volume],
    b=[bid_price, whole_lot_volume, lot_volume]. Parser uses a[0], a[2], b[0], b[2].
    """
    return {
        "error": [],
        "result": {
            "XXBTZUSD": {
                "a": [ask, "1", "1.000"],
                "b": [bid, "1", "1.000"],
            },
        },
    }


def _coinbase_book_response(bid: str, ask: str) -> dict:
    """Build a minimal valid Coinbase product_book response for BTC-USD."""
    return {
        "pricebook": {
            "product_id": "BTC-USD",
            "bids": [{"price": bid, "size": "1.0"}],
            "asks": [{"price": ask, "size": "1.0"}],
            "time": "2024-02-14T15:00:00.000000Z",
        },
    }


def _gemini_book_response(bid: str, ask: str) -> dict:
    """Build a minimal valid Gemini /v1/book response for btcusd."""
    return {
        "bids": [{"price": bid, "amount": "1.0", "timestamp": "1707900000"}],
        "asks": [{"price": ask, "amount": "1.0", "timestamp": "1707900000"}],
    }


# ---------------------------------------------------------------------------
# Connector Factory Helpers
# ---------------------------------------------------------------------------


def _make_kraken(handler, max_retries: int = 1) -> KrakenClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return KrakenClient(
        client=client,
        rate_limiter=RateLimiter(0),
        max_retries=max_retries,
        backoff=FAST_BACKOFF,
    )


def _make_coinbase(handler, max_retries: int = 1) -> CoinbaseClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return CoinbaseClient(
        client=client,
        rate_limiter=RateLimiter(0),
        max_retries=max_retries,
        backoff=FAST_BACKOFF,
    )


def _make_gemini(handler, max_retries: int = 1) -> GeminiClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return GeminiClient(
        client=client,
        rate_limiter=RateLimiter(0),
        max_retries=max_retries,
        backoff=FAST_BACKOFF,
    )


def _write_config(tmp_path: Path, venues: list[str], email_enabled: bool = False) -> str:
    """Write a synthetic config.yaml and return its path as str.

    Uses the real fee_schedules.json from importlib.resources (loaded inside
    load_config) so that fee math exercises production fee structures.
    """
    venue_configs = "\n".join(_VENUE_CONFIG_BLOCK.format(venue=v) for v in venues)
    fees = "\n".join(_FEE_BLOCK.format(venue=v) for v in venues)
    recipients = "['test@example.com']" if email_enabled else "[]"

    yaml_text = INTEGRATION_CFG_TEMPLATE.format(
        venues=", ".join(venues),
        venue_configs=venue_configs,
        fees=fees,
        email_enabled="true" if email_enabled else "false",
        recipients=recipients,
    )
    cfg_path = tmp_path / "integration_config.yaml"
    cfg_path.write_text(yaml_text)
    return str(cfg_path)


# ---------------------------------------------------------------------------
# Patch decorator: deterministic now_ms() across all 3 import sites
# ---------------------------------------------------------------------------


def _patch_now_ms(func):
    """Patch now_ms() in all modules that import it.

    Three modules import now_ms directly:
      - uscryptoarb.orchestration.scan_loop (staleness timestamp)
      - uscryptoarb.connectors.connector_base (_fetch_tickers_per_pair ts_local_ms)
      - uscryptoarb.connectors.kraken.client (fetch_tickers ts_local_ms)
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        with patch("uscryptoarb.orchestration.scan_loop.now_ms", return_value=FIXED_TS_MS):
            with patch("uscryptoarb.connectors.connector_base.now_ms", return_value=FIXED_TS_MS):
                with patch("uscryptoarb.connectors.kraken.client.now_ms", return_value=FIXED_TS_MS):
                    return func(*args, **kwargs)

    return wrapper


# ===========================================================================
# Test 1: No opportunity — all exchanges return similar prices
# ===========================================================================


class TestNoOpportunitySimilarPrices:
    """All 3 exchanges have near-identical BTC/USD prices.

    Best cross-exchange spread is negligible (< 0.55% threshold after fees).
    Pipeline should return zero opportunities.
    """

    @_patch_now_ms
    def test_no_opportunity_all_prices_similar(self, tmp_path: Path) -> None:
        # Prices: Kraken bid=99500/ask=99600, Coinbase bid=99480/ask=99580,
        # Gemini bid=99490/ask=99590.
        # Best raw spread: best_bid=99500 (kraken), best_ask=99580 (coinbase)
        # Raw return = (99500 - 99580) / 99580 ≈ -0.08% (NEGATIVE — no arb)

        def kraken_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_kraken_ticker_response("99500.0", "99600.0"),
            )

        def coinbase_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_coinbase_book_response("99480.0", "99580.0"),
            )

        def gemini_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_gemini_book_response("99490.0", "99590.0"),
            )

        connectors = {
            "kraken": _make_kraken(kraken_handler),
            "coinbase": _make_coinbase(coinbase_handler),
            "gemini": _make_gemini(gemini_handler),
        }

        cfg_path = _write_config(tmp_path, ["kraken", "coinbase", "gemini"])
        config = load_config(cfg_path)
        # Relax staleness to match our huge max_staleness_ms
        config = replace(
            config,
            arbitrage=replace(config.arbitrage, max_staleness_ms=10_000_000_000_000),
        )

        async def run() -> None:
            opportunities = await run_scan_cycle(connectors, config, run_id="integ-noarb")
            assert opportunities == [], (
                f"Expected no opportunities but got {len(opportunities)}: "
                f"{[(o.buy_venue, o.sell_venue, float(o.return_net)) for o in opportunities]}"
            )

        asyncio.run(run())


# ===========================================================================
# Test 2: Opportunity detected — large price divergence + email triggered
# ===========================================================================


class TestOpportunityDetectedEmailSent:
    """Two exchanges with ~2.4% price divergence.

    Kraken: bid=99000/ask=99100 (cheap — buy here)
    Coinbase: bid=101500/ask=101600 (expensive — sell here)

    Raw spread = (101500 - 99100) / 99100 ≈ 2.42%, well above 0.55%.
    Should detect opportunity and trigger email notification.
    """

    @_patch_now_ms
    def test_opportunity_detected_and_email_triggered(self, tmp_path: Path) -> None:
        def kraken_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_kraken_ticker_response("99000.0", "99100.0"),
            )

        def coinbase_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_coinbase_book_response("101500.0", "101600.0"),
            )

        connectors = {
            "kraken": _make_kraken(kraken_handler),
            "coinbase": _make_coinbase(coinbase_handler),
        }

        cfg_path = _write_config(
            tmp_path,
            ["kraken", "coinbase"],
            email_enabled=True,
        )
        config = load_config(cfg_path)
        config = replace(
            config,
            arbitrage=replace(config.arbitrage, max_staleness_ms=10_000_000_000_000),
        )

        async def run() -> None:
            # --- Pipeline detection ---
            opportunities = await run_scan_cycle(connectors, config, run_id="integ-arb")

            assert len(opportunities) == 1, f"Expected 1 opportunity, got {len(opportunities)}"
            opp = opportunities[0]

            # Direction: buy cheap on kraken (ask=99100), sell expensive on coinbase (bid=101500)
            assert opp.buy_venue == "kraken", f"Expected buy_venue=kraken, got {opp.buy_venue}"
            assert opp.sell_venue == "coinbase", (
                f"Expected sell_venue=coinbase, got {opp.sell_venue}"
            )
            assert opp.pair == "BTC/USD"
            assert opp.buy_price == Decimal("99100.0")
            assert opp.sell_price == Decimal("101500.0")
            assert isinstance(opp, ArbOpportunity)

            # return_net must exceed the 0.55% threshold (after all fees)
            assert opp.return_net > Decimal("0.0055"), (
                f"return_net {opp.return_net} should exceed threshold 0.0055"
            )
            # Sanity: return_raw > return_grs > return_net (fees erode returns)
            assert opp.return_raw >= opp.return_grs >= opp.return_net

            # --- Email notification ---
            email_cfg = EmailConfig(
                enabled=True,
                smtp_host="smtp.gmail.com",
                smtp_port=587,
                from_addr="bot@example.com",
                recipients=("test@example.com",),
                password="fake-password",
            )
            with patch("uscryptoarb.notification.email._send_smtp") as mock_smtp:
                await send_alert(opp, email_cfg)
                mock_smtp.assert_called_once()

                # Verify email content
                call_args = mock_smtp.call_args
                # _send_smtp(host, port, from_addr, password, recipients, subject, body)
                subject_arg = call_args[0][5]
                assert "ARB: BTC/USD" in subject_arg

            # Also verify format_opportunity_email independently
            subject, body = format_opportunity_email(opp)
            assert "ARB: BTC/USD" in subject
            assert "Buy: kraken" in body
            assert "Sell: coinbase" in body

        asyncio.run(run())


# ===========================================================================
# Test 3: Partial failure — one exchange HTTP 500, remaining 2 still work
# ===========================================================================


class TestPartialFailureGracefulDegradation:
    """One exchange fails (HTTP 500), system degrades to remaining 2.

    Coinbase returns HTTP 500 on all requests.
    Kraken and Gemini have large spread → opportunity found between them.
    """

    @_patch_now_ms
    def test_one_exchange_500_uses_remaining_two(self, tmp_path: Path) -> None:
        def kraken_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_kraken_ticker_response("99000.0", "99100.0"),
            )

        def coinbase_500_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        def gemini_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_gemini_book_response("101500.0", "101600.0"),
            )

        connectors = {
            "kraken": _make_kraken(kraken_handler),
            "coinbase": _make_coinbase(coinbase_500_handler, max_retries=1),
            "gemini": _make_gemini(gemini_handler),
        }

        cfg_path = _write_config(tmp_path, ["kraken", "coinbase", "gemini"])
        config = load_config(cfg_path)
        config = replace(
            config,
            arbitrage=replace(config.arbitrage, max_staleness_ms=10_000_000_000_000),
        )

        async def run() -> None:
            opportunities = await run_scan_cycle(connectors, config, run_id="integ-partial")

            # Should find opportunity between kraken and gemini
            assert len(opportunities) == 1, (
                f"Expected 1 opportunity from kraken/gemini, got {len(opportunities)}"
            )
            opp = opportunities[0]
            assert opp.buy_venue == "kraken"
            assert opp.sell_venue == "gemini"
            assert opp.return_net > Decimal("0.0055")

            # Coinbase must NOT appear in the result
            assert "coinbase" not in (opp.buy_venue, opp.sell_venue)

        asyncio.run(run())


# ===========================================================================
# Test 4: Timeout — exchange times out, insufficient venues for comparison
# ===========================================================================


class TestTimeoutInsufficientVenues:
    """One of two exchanges times out → only 1 venue has data → no comparison possible.

    Kraken returns valid data. Gemini raises TimeoutException on all requests.
    With only 1 venue, run_scan_cycle skips the pair (needs >= 2 venues).
    """

    @_patch_now_ms
    def test_exchange_timeout_returns_no_opportunities(self, tmp_path: Path) -> None:
        def kraken_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=_kraken_ticker_response("99500.0", "99600.0"),
            )

        def gemini_timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("connection timed out")

        connectors = {
            "kraken": _make_kraken(kraken_handler),
            "gemini": _make_gemini(gemini_timeout_handler, max_retries=1),
        }

        cfg_path = _write_config(tmp_path, ["kraken", "gemini"])
        config = load_config(cfg_path)
        config = replace(
            config,
            arbitrage=replace(config.arbitrage, max_staleness_ms=10_000_000_000_000),
        )

        async def run() -> None:
            # Must not raise — graceful degradation
            opportunities = await run_scan_cycle(connectors, config, run_id="integ-timeout")
            assert opportunities == [], (
                f"Expected no opportunities with only 1 venue, got {len(opportunities)}"
            )

        asyncio.run(run())
