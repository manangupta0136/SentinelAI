"""Application traffic profiles and traffic mix definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ApplicationProfile:
    """Defines the traffic characteristics of an enterprise application.

    Attributes:
        name: Application name (erp, database, video_conferencing, etc.).
        description: Human-readable description.
        base_bandwidth_mbps: Nominal bandwidth consumption.
        burst_factor: Multiplier for traffic bursts.
        burst_probability: Probability of a burst occurring in any tick.
        priority: Traffic class priority (high, medium, low).
        time_of_day_profile: List of ``{"hour": h, "multiplier": m}`` entries.
        cpu_load_factor: Fraction of bandwidth that translates to CPU load.
        memory_load_factor: Fraction of bandwidth that translates to memory load.
        latency_sensitivity_ms: Maximum acceptable latency before QoE degrades.
    """

    name: str
    description: str = ""
    base_bandwidth_mbps: float = 10.0
    burst_factor: float = 2.0
    burst_probability: float = 0.1
    priority: str = "medium"
    time_of_day_profile: List[Dict[str, float]] = field(default_factory=list)
    cpu_load_factor: float = 0.1
    memory_load_factor: float = 0.08
    latency_sensitivity_ms: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the profile to a dictionary.

        Returns:
            Dictionary of profile attributes.
        """
        return {
            "name": self.name,
            "description": self.description,
            "base_bandwidth_mbps": self.base_bandwidth_mbps,
            "burst_factor": self.burst_factor,
            "burst_probability": self.burst_probability,
            "priority": self.priority,
            "cpu_load_factor": self.cpu_load_factor,
            "memory_load_factor": self.memory_load_factor,
            "latency_sensitivity_ms": self.latency_sensitivity_ms,
        }


@dataclass
class TrafficMix:
    """Container for all application profiles active in the simulation.

    Attributes:
        profiles: List of ApplicationProfile instances.
        weekend_multiplier: Global traffic multiplier on weekends.
        office_hours_start: Hour when office hours begin.
        office_hours_end: Hour when office hours end.
        peak_start: Hour when peak period starts.
        peak_end: Hour when peak period ends.
    """

    profiles: List[ApplicationProfile] = field(default_factory=list)
    weekend_multiplier: float = 0.3
    office_hours_start: int = 8
    office_hours_end: int = 18
    peak_start: int = 10
    peak_end: int = 15

    def get_profile(self, name: str) -> ApplicationProfile:
        """Look up a profile by name.

        Args:
            name: Profile name.

        Returns:
            Matching ApplicationProfile.

        Raises:
            KeyError: If no profile matches.
        """
        for p in self.profiles:
            if p.name == name:
                return p
        raise KeyError(f"Application profile not found: {name}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the traffic mix to a dictionary.

        Returns:
            Dictionary with profile list and global settings.
        """
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "weekend_multiplier": self.weekend_multiplier,
            "office_hours_start": self.office_hours_start,
            "office_hours_end": self.office_hours_end,
        }
