from __future__ import annotations

import asyncio
import logging
import uuid
from contextlib import AsyncExitStack
from decimal import Decimal
from typing import cast

import httpx

from uscryptoarb.calculation.calc_types import ArbOpportunity
from uscryptoarb.calculation.returns import calc_return_raw
from uscryptoarb.connectors.coinbase.client import CoinbaseClient
from uscryptoarb.connectors.connector_base import BaseAsyncConnector, ExchangeConnector
from uscryptoarb.connectors.gemini.client import GeminiClient
from uscryptoarb.connectors.kraken.client import KrakenClient
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.misc.time_utils import now_ms
from uscryptoarb.notification.email import send_alert
from uscryptoarb.orchestration.config import ScannerConfig
from uscryptoarb.strategy.trade_finder import RejectionReason, find_trades_to_execute

logger = logging.getLogger(__name__)


_CONNECTOR_REGISTRY: dict[str, type[BaseAsyncConnector]] = {
    "kraken": KrakenClient,
    "coinbase": CoinbaseClient,
    "gemini": GeminiClient,
}


async def create_connectors(
    config: ScannerConfig,
    stack: AsyncExitStack,
) -> dict[str, ExchangeConnector]:
    """Create exchange connectors for all configured venues.

    Uses _CONNECTOR_REGISTRY to map venue names to connector classes.
    All connectors share the BaseAsyncConnector constructor signature (DEC-018).
    """
    connectors: dict[str, ExchangeConnector] = {}
    for venue in config.venues:
        connector_cls = _CONNECTOR_REGISTRY.get(venue)
        if connector_cls is None:
            logger.warning("Unknown venue in config, skipping connector creation: %s", venue)
            continue

        venue_cfg = config.venue_configs[venue]
        http_client = await stack.enter_async_context(httpx.AsyncClient())
        limiter = RateLimiter(min_interval_ms=venue_cfg.rate_limit_ms)

        concrete_connector_cls = cast(
            type[KrakenClient] | type[CoinbaseClient] | type[GeminiClient],
            connector_cls,
        )
        connectors[venue] = concrete_connector_cls(
            client=http_client,
            rate_limiter=limiter,
            timeout_s=venue_cfg.timeout_s,
            max_retries=venue_cfg.max_retries,
        )

    return connectors


async def fetch_all_venues(
    connectors: dict[str, ExchangeConnector],
    pairs: list[str],
    run_id: str,
) -> dict[str, dict[str, TopOfBook]]:
    venues = list(connectors)
    tasks = [connectors[venue].fetch_tickers(pairs) for venue in venues]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out: dict[str, dict[str, TopOfBook]] = {}
    for venue, result in zip(venues, results, strict=True):
        if isinstance(result, BaseException):
            logger.warning("[%s] Venue fetch failed for %s: %s", run_id, venue, result)
            continue
        out[venue] = result

    logger.info("[%s] Fetched %d venues: %s", run_id, len(out), list(out.keys()))
    return out


def reorganize_by_pair(
    venue_data: dict[str, dict[str, TopOfBook]],
    pairs: list[str],
) -> dict[str, dict[str, TopOfBook]]:
    by_pair: dict[str, dict[str, TopOfBook]] = {}
    for pair in pairs:
        pair_map: dict[str, TopOfBook] = {}
        for venue, venue_tobs in venue_data.items():
            tob = venue_tobs.get(pair)
            if tob is not None:
                pair_map[venue] = tob
        if pair_map:
            by_pair[pair] = pair_map
    return by_pair


def _log_pair_spreads(
    pair: str,
    tobs_by_venue: dict[str, TopOfBook],
    threshold: Decimal,
    run_id: str,
) -> None:
    """Log bid/ask per venue and best raw cross-exchange spread.

    Provides per-pair diagnostics so operators can verify the pipeline
    is calculating correctly and see how close markets are to threshold.
    Runs on every scan cycle (dry-run and continuous).

    Uses calc_return_raw() from the calculation layer to compute the
    best-case spread (Coding Rule 10.2 — single source of truth).

    Args:
        pair: Canonical pair string (e.g. "BTC/USD").
        tobs_by_venue: {venue_name: TopOfBook} for this pair. Must have >= 2 entries.
        threshold: Configured minimum return_net for alerting.
        run_id: Correlation ID for this scan cycle.
    """
    parts = []
    for venue, tob in sorted(tobs_by_venue.items()):
        parts.append(f"{venue} bid={tob.bid_px} ask={tob.ask_px}")

    best_bid = max(tob.bid_px for tob in tobs_by_venue.values())
    best_ask = min(tob.ask_px for tob in tobs_by_venue.values())
    raw_spread = calc_return_raw(buy_price=best_ask, sell_price=best_bid)

    spread_pct = raw_spread * Decimal("100")
    threshold_pct = threshold * Decimal("100")
    sign = "+" if spread_pct >= 0 else ""

    venue_str = " | ".join(parts)
    logger.info(
        "[%s] %s: %s | best_spread=%s%s%% (threshold=%s%%)",
        run_id,
        pair,
        venue_str,
        sign,
        f"{spread_pct:.3f}",
        f"{threshold_pct:.3f}",
    )


async def run_scan_cycle(
    connectors: dict[str, ExchangeConnector],
    config: ScannerConfig,
    run_id: str,
) -> list[ArbOpportunity]:
    venue_data = await fetch_all_venues(connectors, list(config.pairs), run_id)
    by_pair = reorganize_by_pair(venue_data, list(config.pairs))
    ts_now = now_ms()
    opportunities: list[ArbOpportunity] = []

    for pair in config.pairs:
        tobs_by_venue = by_pair.get(pair, {})
        if len(tobs_by_venue) < 2:
            logger.debug("[%s] Skipping %s: only %d venue(s)", run_id, pair, len(tobs_by_venue))
            continue

        _log_pair_spreads(pair, tobs_by_venue, config.arbitrage.threshold, run_id)

        fees_by_venue = config.fees_by_pair_venue.get(pair)
        if fees_by_venue is None:
            logger.warning("[%s] Missing fees for %s; skipping", run_id, pair)
            continue

        trade_amount = config.arbitrage.trade_amounts[pair]

        try:
            opp = find_trades_to_execute(
                tobs_by_venue=tobs_by_venue,
                fees_by_venue=fees_by_venue,
                threshold=config.arbitrage.threshold,
                trade_amount=trade_amount,
                ts_calculated_ms=ts_now,
                max_staleness_ms=config.arbitrage.max_staleness_ms,
            )
        except Exception as exc:
            logger.error("[%s] Unexpected strategy error for %s: %s", run_id, pair, exc)
            continue

        if pair in config.debug.trace_pairs:
            logger.debug(
                "[%s] TRACE pair=%s tobs=%s fees=%s result=%s",
                run_id,
                pair,
                tobs_by_venue,
                list(fees_by_venue.keys()),
                opp,
            )

        if isinstance(opp, RejectionReason):
            if pair in config.debug.trace_pairs or config.debug.enabled:
                logger.debug(
                    "[%s] %s: no opportunity — %s",
                    run_id,
                    pair,
                    opp.name,
                )
            continue

        opportunities.append(opp)

    logger.info(
        "[%s] Scan complete: %d pairs, %d opportunities",
        run_id,
        len(config.pairs),
        len(opportunities),
    )
    return opportunities


async def run_scan_loop(config: ScannerConfig, shutdown_event: asyncio.Event) -> None:
    async with AsyncExitStack() as stack:
        connectors = await create_connectors(config, stack)
        if not connectors:
            logger.error("No connectors created — exiting")
            return

        logger.info("Scanner started: %d venues, %d pairs", len(connectors), len(config.pairs))
        cycle_count = 0

        while not shutdown_event.is_set():
            cycle_count += 1
            run_id = uuid.uuid4().hex[:12]
            try:
                opportunities = await run_scan_cycle(connectors, config, run_id)
                for opp in opportunities:
                    try:
                        await send_alert(opp, config.email)
                    except Exception as exc:
                        logger.error("[%s] Email failed for %s: %s", run_id, opp.pair, exc)
            except Exception as exc:
                logger.error("[%s] Scan cycle failed: %s", run_id, exc)

            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=config.polling.interval_seconds,
                )
            except TimeoutError:
                pass

        logger.info("Scanner stopped after %d cycles", cycle_count)
