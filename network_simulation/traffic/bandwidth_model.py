"""Bandwidth consumption model driven by application profiles.

Computes the total offered load on each link by summing per-application
traffic volumes after applying time-of-day and burst logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from network_simulation.traffic.application_profiles import (
    ApplicationProfile,
    TrafficMix,
)
from network_simulation.utils.helpers import interpolate_time_of_day, is_weekend
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class BandwidthModel:
    """Calculates bandwidth demand per application at a given simulation time.

    The model uses time-of-day interpolation from the profile, applies
    weekend multipliers, and optionally adds random bursts.
    """

    def __init__(
        self,
        traffic_mix: TrafficMix,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        """Initialise the bandwidth model.

        Args:
            traffic_mix: Configured TrafficMix with application profiles.
            rng: NumPy random generator for burst sampling.
        """
        self._traffic_mix = traffic_mix
        self._rng = rng if rng is not None else np.random.default_rng()

    def compute_demand(
        self,
        profile: ApplicationProfile,
        hour: float,
        is_weekend_day: bool,
        device_weight: float = 1.0,
    ) -> float:
        """Compute bandwidth demand for a single application profile.

        Args:
            profile: The application profile.
            hour: Current hour of day (0–24).
            is_weekend_day: Whether today is a weekend.
            device_weight: Per-role traffic multiplier.

        Returns:
            Bandwidth demand in Mbps.
        """
        multiplier = interpolate_time_of_day(hour, profile.time_of_day_profile)
        if is_weekend_day:
            multiplier *= self._traffic_mix.weekend_multiplier
        base = profile.base_bandwidth_mbps * multiplier * device_weight
        if self._rng.uniform() < profile.burst_probability:
            base *= profile.burst_factor
        return base

    def compute_total_demand(
        self,
        hour: float,
        is_weekend_day: bool,
        device_weight: float = 1.0,
    ) -> Dict[str, float]:
        """Compute bandwidth demand for every application profile.

        Args:
            hour: Current hour of day.
            is_weekend_day: Whether today is a weekend.
            device_weight: Per-role traffic multiplier.

        Returns:
            Dictionary mapping profile name to bandwidth demand in Mbps.
        """
        demands = {}
        for profile in self._traffic_mix.profiles:
            demands[profile.name] = self.compute_demand(
                profile, hour, is_weekend_day, device_weight
            )
        return demands

    def is_peak_hour(self, hour: float) -> bool:
        """Check if the given hour falls within the configured peak window.

        Args:
            hour: Current hour of day.

        Returns:
            True if within peak window.
        """
        return (
            self._traffic_mix.peak_start <= hour < self._traffic_mix.peak_end
        )
