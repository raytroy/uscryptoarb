from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import AsyncExitStack

import httpx

from uscryptoarb.calculation.types import ArbOpportunity
from uscryptoarb.connectors.base import ExchangeConnector
from uscryptoarb.connectors.coinbase.client import CoinbaseClient
from uscryptoarb.connectors.kraken.client import KrakenClient
from uscryptoarb.http.rate_limiter import RateLimiter
from uscryptoarb.marketdata.topofbook import TopOfBook
from uscryptoarb.notification.email import send_alert
from uscryptoarb.orchestration.config import ScannerConfig
from uscryptoarb.strategy.scanner import find_trades_to_execute

logger = logging.getLogger(__name__)


async def create_connectors(
    config: ScannerConfig,
    stack: AsyncExitStack,
) -> dict[str, ExchangeConnector]:
    connectors: dict[str, ExchangeConnector] = {}
    for venue in config.venues:
        venue_cfg = config.venue_configs[venue]
        http_client = await stack.enter_async_context(httpx.AsyncClient())
        limiter = RateLimiter(min_interval_ms=venue_cfg.rate_limit_ms)

        if venue == "kraken":
            connectors[venue] = KrakenClient(
                client=http_client,
                rate_limiter=limiter,
                timeout_s=venue_cfg.timeout_s,
                max_retries=venue_cfg.max_retries,
            )
        elif venue == "coinbase":
            connectors[venue] = CoinbaseClient(
                client=http_client,
                rate_limiter=limiter,
                timeout_s=venue_cfg.timeout_s,
                max_retries=venue_cfg.max_retries,
            )
        else:
            logger.warning("Unknown venue in config, skipping connector creation: %s", venue)

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


async def run_scan_cycle(
    connectors: dict[str, ExchangeConnector],
    config: ScannerConfig,
    run_id: str,
) -> list[ArbOpportunity]:
    venue_data = await fetch_all_venues(connectors, list(config.pairs), run_id)
    by_pair = reorganize_by_pair(venue_data, list(config.pairs))
    ts_now = int(time.time() * 1000)
    opportunities: list[ArbOpportunity] = []

    for pair in config.pairs:
        tobs_by_venue = by_pair.get(pair, {})
        if len(tobs_by_venue) < 2:
            logger.debug("[%s] Skipping %s: only %d venue(s)", run_id, pair, len(tobs_by_venue))
            continue

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

        if opp is not None:
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
