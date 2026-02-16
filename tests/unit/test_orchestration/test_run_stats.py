"""Tests for RunStats accumulator."""

from __future__ import annotations

from uscryptoarb.orchestration.run_stats import RunStats


class TestRecordCycle:
    def test_increments_counts(self) -> None:
        stats = RunStats()
        stats.record_cycle(duration_ms=150.0, opportunities=2, venue_errors={})
        assert stats.cycles_completed == 1
        assert stats.opportunities_detected == 2
        assert stats.cycle_durations_ms == [150.0]

    def test_accumulates_across_cycles(self) -> None:
        stats = RunStats()
        stats.record_cycle(100.0, 1, {})
        stats.record_cycle(200.0, 3, {})
        assert stats.cycles_completed == 2
        assert stats.opportunities_detected == 4
        assert stats.cycle_durations_ms == [100.0, 200.0]

    def test_venue_errors_accumulate(self) -> None:
        stats = RunStats()
        stats.record_cycle(100.0, 0, {"kraken": 1})
        stats.record_cycle(100.0, 0, {"kraken": 1, "coinbase": 1})
        assert stats.errors_by_venue == {"kraken": 2, "coinbase": 1}

    def test_bounds_duration_history(self) -> None:
        stats = RunStats()
        for i in range(120):
            stats.record_cycle(float(i), 0, {})
        assert len(stats.cycle_durations_ms) == 100
        assert stats.cycle_durations_ms[0] == 20.0
        assert stats.cycle_durations_ms[-1] == 119.0
        assert stats.cycles_completed == 120


class TestSummaryLine:
    def test_zero_cycles(self) -> None:
        stats = RunStats()
        line = stats.summary_line()
        assert line == "0 cycles, 0 opportunities, 0 errors, avg_cycle=0ms"

    def test_format_with_data(self) -> None:
        stats = RunStats()
        stats.record_cycle(100.0, 1, {"kraken": 1})
        stats.record_cycle(200.0, 2, {})
        line = stats.summary_line()
        assert "2 cycles" in line
        assert "3 opportunities" in line
        assert "1 errors" in line
        assert "avg_cycle=150ms" in line

    def test_no_errors_shows_zero(self) -> None:
        stats = RunStats()
        stats.record_cycle(50.0, 0, {})
        assert "0 errors" in stats.summary_line()
