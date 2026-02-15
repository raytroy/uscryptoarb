"""
CLI entry point: python -m uscryptoarb

Starts the arbitrage detection scanner. This is the Mathematica RunFinal[]
equivalent for Phase 1 (detection + alerts only, no execution).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from contextlib import AsyncExitStack
from dataclasses import replace

from uscryptoarb.orchestration.config import DebugConfig, ScannerConfig, load_config
from uscryptoarb.orchestration.scanner import create_connectors, run_scan_cycle, run_scan_loop

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m uscryptoarb")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--trace-pair", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default=None)
    return parser.parse_args()


def setup_logging(level: str, trace_pairs: list[str]) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    if trace_pairs:
        logging.getLogger("uscryptoarb.orchestration.scanner").setLevel(logging.DEBUG)


async def _run(config: ScannerConfig, dry_run: bool) -> None:
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except NotImplementedError:
            pass

    if dry_run:
        async with AsyncExitStack() as stack:
            connectors = await create_connectors(config, stack)
            opps = await run_scan_cycle(connectors, config, run_id="dryrun")
            if not opps:
                logger.info("DRY RUN: no opportunities found")
            for opp in opps:
                logger.info(
                    "DRY RUN opportunity: %s %s buy %s @ %s sell %s @ %s return_net=%s",
                    opp.pair,
                    opp.market_currency,
                    opp.buy_venue,
                    opp.buy_price,
                    opp.sell_venue,
                    opp.sell_price,
                    opp.return_net,
                )
        return

    await run_scan_loop(config, shutdown_event)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    debug_cfg = config.debug
    if args.log_level is not None or args.trace_pair:
        debug_cfg = DebugConfig(
            enabled=debug_cfg.enabled,
            trace_pairs=tuple(args.trace_pair) if args.trace_pair else debug_cfg.trace_pairs,
            log_level=args.log_level if args.log_level else debug_cfg.log_level,
        )
        config = replace(config, debug=debug_cfg)

    setup_logging(config.debug.log_level, list(config.debug.trace_pairs))
    asyncio.run(_run(config, args.dry_run))


if __name__ == "__main__":
    main()
