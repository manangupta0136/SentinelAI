"""Timestamp utilities for the simulation.

All telemetry records use UTC ISO 8601 timestamps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SimulationTimestamp:
    """Wraps a simulation timestamp with tick and wall-clock information.

    Attributes:
        tick: Simulation tick number (0-based).
        wall_clock: Corresponding wall-clock datetime (UTC).
        tick_interval_seconds: Seconds per tick.
    """

    tick: int
    wall_clock: datetime
    tick_interval_seconds: int = 60

    @classmethod
    def from_tick(
        cls,
        tick: int,
        start_time: Optional[datetime] = None,
        tick_interval_seconds: int = 60,
    ) -> SimulationTimestamp:
        """Create a timestamp from a tick number and optional start time.

        Args:
            tick: Simulation tick number.
            start_time: Simulation start datetime (UTC). Defaults to
                ``1970-01-01T00:00:00Z``.
            tick_interval_seconds: Wall-clock seconds per tick.

        Returns:
            A SimulationTimestamp instance.
        """
        if start_time is None:
            start_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        wall_clock = datetime.fromtimestamp(
            start_time.timestamp() + tick * tick_interval_seconds,
            tz=timezone.utc,
        )
        return cls(
            tick=tick,
            wall_clock=wall_clock,
            tick_interval_seconds=tick_interval_seconds,
        )

    @property
    def iso_format(self) -> str:
        """Return the timestamp in ISO 8601 format.

        Returns:
            ISO 8601 string (e.g. ``2025-01-15T14:30:00Z``).
        """
        return self.wall_clock.strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self) -> dict:
        """Serialize to dictionary.

        Returns:
            Dictionary with tick and iso timestamp.
        """
        return {
            "tick": self.tick,
            "timestamp": self.iso_format,
        }
