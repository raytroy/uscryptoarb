"""Tests for __main__.py setup_logging and CLI argument handling."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from uscryptoarb.__main__ import setup_logging
from uscryptoarb.orchestration.config import LoggingConfig


def _clear_root_handlers() -> None:
    """Remove all handlers from root logger for test isolation."""
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()


class TestSetupLogging:
    def setup_method(self) -> None:
        _clear_root_handlers()

    def teardown_method(self) -> None:
        _clear_root_handlers()

    def test_stdout_only_when_no_file(self) -> None:
        cfg = LoggingConfig(file_path=None, max_bytes=1024, backup_count=1, stats_interval=20)
        setup_logging("INFO", [], cfg, None)
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)
        assert not isinstance(root.handlers[0], RotatingFileHandler)

    def test_file_handler_added_from_config(self, tmp_path) -> None:
        log_file = str(tmp_path / "test.log")
        cfg = LoggingConfig(file_path=log_file, max_bytes=1024, backup_count=1, stats_interval=20)
        setup_logging("INFO", [], cfg, None)
        root = logging.getLogger()
        assert len(root.handlers) == 2
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_cli_override_takes_precedence(self, tmp_path) -> None:
        config_file = str(tmp_path / "config.log")
        cli_file = str(tmp_path / "cli.log")
        cfg = LoggingConfig(
            file_path=config_file,
            max_bytes=1024,
            backup_count=1,
            stats_interval=20,
        )
        setup_logging("INFO", [], cfg, cli_file)
        root = logging.getLogger()
        file_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].baseFilename == cli_file

    def test_trace_pairs_sets_scan_loop_debug(self) -> None:
        cfg = LoggingConfig(file_path=None, max_bytes=1024, backup_count=1, stats_interval=20)
        setup_logging("INFO", ["BTC/USD"], cfg, None)
        scan_logger = logging.getLogger("uscryptoarb.orchestration.scan_loop")
        assert scan_logger.level == logging.DEBUG
