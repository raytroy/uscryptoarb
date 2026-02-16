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
from logging.handlers import RotatingFileHandler

from uscryptoarb.orchestration.config import DebugConfig, LoggingConfig, ScannerConfig, load_config
from uscryptoarb.orchestration.scan_loop import create_connectors, run_scan_cycle, run_scan_loop

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m uscryptoarb")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--trace-pair", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--log-level", default=None)
    parser.add_argument("--log-file", default=None, help="Log file path (overrides config)")
    parser.add_argument(
        "--stats-interval",
        type=int,
        default=None,
        help="Cycles between stats summaries",
    )
    return parser.parse_args()


def setup_logging(
    level: str,
    trace_pairs: list[str],
    logging_cfg: LoggingConfig,
    log_file_override: str | None,
) -> None:
    """Configure root logger with stdout and optional file handler.

    Both handlers use the same format (Coding Rule 10.2 — single source
    of truth for formatting). File handler uses RotatingFileHandler from
    stdlib logging.handlers.

    Args:
        level: Log level string (e.g. "INFO", "DEBUG").
        trace_pairs: Pairs to enable DEBUG logging for.
        logging_cfg: Logging config from config.yaml.
        log_file_override: CLI --log-file value (takes precedence over config).
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    file_path = log_file_override or logging_cfg.file_path
    if file_path is not None:
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=logging_cfg.max_bytes,
            backupCount=logging_cfg.backup_count,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    if trace_pairs:
        logging.getLogger("uscryptoarb.orchestration.scan_loop").setLevel(logging.DEBUG)


async def _run(config: ScannerConfig, dry_run: bool, stats_interval: int) -> None:
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
            opps, _venue_errors = await run_scan_cycle(connectors, config, run_id="dryrun")
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

    await run_scan_loop(config, shutdown_event, stats_interval=stats_interval)


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

    stats_interval = (
        args.stats_interval
        if args.stats_interval is not None
        else config.logging.stats_interval
    )

    setup_logging(
        config.debug.log_level,
        list(config.debug.trace_pairs),
        config.logging,
        args.log_file,
    )
    asyncio.run(_run(config, args.dry_run, stats_interval))


if __name__ == "__main__":
    main()
