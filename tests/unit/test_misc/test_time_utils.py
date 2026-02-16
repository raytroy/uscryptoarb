"""Tests for misc/time_utils.py."""

import time

from uscryptoarb.misc.time_utils import now_ms


def test_now_ms_returns_int() -> None:
    result = now_ms()
    assert isinstance(result, int)


def test_now_ms_reasonable_magnitude() -> None:
    """Value should be close to time.time() * 1000."""
    before = int(time.time() * 1000)
    result = now_ms()
    after = int(time.time() * 1000)
    assert before <= result <= after
