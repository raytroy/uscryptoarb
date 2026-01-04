import pytest

from uscryptoarb.http.backoff import BackoffPolicy, compute_delay_ms


def test_backoff_no_jitter_is_exact_and_capped() -> None:
    p = BackoffPolicy(base_ms=100, cap_ms=250, jitter_ratio=0.0)

    assert compute_delay_ms(0, p) == 100
    assert compute_delay_ms(1, p) == 200
    assert compute_delay_ms(2, p) == 250  # capped


def test_backoff_with_jitter_bounds() -> None:
    p = BackoffPolicy(base_ms=1000, cap_ms=10_000, jitter_ratio=0.10)

    # max jitter (r=1.0) => +10%
    assert compute_delay_ms(0, p, rand=lambda: 1.0) == 1100

    # min jitter (r=0.0) => -10%
    assert compute_delay_ms(0, p, rand=lambda: 0.0) == 900


def test_backoff_rejects_negative_attempt() -> None:
    with pytest.raises(ValueError):
        compute_delay_ms(-1)
