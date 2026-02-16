"""Run statistics accumulator for scanner sessions.

Tracks per-session operational metrics in memory. No disk persistence
in Phase 1 — this is purely for logging summaries during operation.

Lives in orchestration layer (I/O/lifecycle concern per DEC-002).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RunStats:
    """Mutable stats accumulator for scanner sessions.

    Intentionally NOT frozen — this is an imperative-shell accumulator
    that is updated in-place during the scan loop lifecycle. It is never
    passed into pure calculation/strategy functions (Coding Rule 2.2
    exception documented here).

    Fields:
        cycles_completed: Total scan cycles finished (success or partial).
        opportunities_detected: Total ArbOpportunity objects found.
        errors_by_venue: Cumulative error count per venue name.
        cycle_durations_ms: Rolling window of recent cycle durations.
        started_at_utc: Session start timestamp.
    """

    started_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # noqa: UP017
    cycles_completed: int = 0
    opportunities_detected: int = 0
    errors_by_venue: dict[str, int] = field(default_factory=dict)
    cycle_durations_ms: list[float] = field(default_factory=list)

    _MAX_DURATION_HISTORY: int = field(default=100, init=False, repr=False)

    def record_cycle(
        self,
        duration_ms: float,
        opportunities: int,
        venue_errors: dict[str, int],
    ) -> None:
        """Record metrics from one completed scan cycle.

        Args:
            duration_ms: Wall-clock duration of the cycle.
            opportunities: Number of ArbOpportunity objects found this cycle.
            venue_errors: {venue_name: error_count} for venues that failed.
        """
        self.cycles_completed += 1
        self.opportunities_detected += opportunities
        for venue, count in venue_errors.items():
            self.errors_by_venue[venue] = self.errors_by_venue.get(venue, 0) + count
        self.cycle_durations_ms.append(duration_ms)
        if len(self.cycle_durations_ms) > self._MAX_DURATION_HISTORY:
            self.cycle_durations_ms = self.cycle_durations_ms[-self._MAX_DURATION_HISTORY :]

    def summary_line(self) -> str:
        """One-line summary suitable for periodic and shutdown logging."""
        if self.cycle_durations_ms:
            avg_ms = sum(self.cycle_durations_ms) / len(self.cycle_durations_ms)
        else:
            avg_ms = 0.0
        total_errors = sum(self.errors_by_venue.values())
        return (
            f"{self.cycles_completed} cycles, "
            f"{self.opportunities_detected} opportunities, "
            f"{total_errors} errors, "
            f"avg_cycle={avg_ms:.0f}ms"
        )
