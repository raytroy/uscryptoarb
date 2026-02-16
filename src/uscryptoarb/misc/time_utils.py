"""Timestamp utilities.

Centralizes the common pattern of getting current time in milliseconds.
Replaces 4 inline copies of `int(time.time() * 1000)`.
"""

from __future__ import annotations

import time


def now_ms() -> int:
    """Current time as milliseconds since Unix epoch."""
    return int(time.time() * 1000)
