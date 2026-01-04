from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    """
    Exponential backoff policy (milliseconds).

    attempt=0 -> base_ms
    attempt=1 -> 2*base_ms
    attempt=2 -> 4*base_ms
    ... capped at cap_ms

    Jitter is symmetric (+/- jitter_ratio).
    """
    base_ms: int = 250
    cap_ms: int = 5_000
    jitter_ratio: float = 0.10


DEFAULT_BACKOFF_POLICY = BackoffPolicy()


def compute_delay_ms(
    attempt: int,
    policy: BackoffPolicy = DEFAULT_BACKOFF_POLICY,
    rand: Callable[[], float] = random.random,
) -> int:
    if attempt < 0:
        raise ValueError("attempt must be >= 0")
    if policy.base_ms <= 0:
        raise ValueError("base_ms must be > 0")
    if policy.cap_ms <= 0:
        raise ValueError("cap_ms must be > 0")
    if policy.jitter_ratio < 0:
        raise ValueError("jitter_ratio must be >= 0")

    raw = policy.base_ms * (2**attempt)
    capped = min(raw, policy.cap_ms)

    if policy.jitter_ratio == 0:
        return int(capped)

    # rand() in [0, 1) -> jitter multiplier in [1-j, 1+j)
    r = rand()
    j = policy.jitter_ratio
    mult = 1.0 + j * (2.0 * r - 1.0)

    jittered = int(capped * mult)
    if jittered < 0:
        return 0
    return min(jittered, policy.cap_ms)
