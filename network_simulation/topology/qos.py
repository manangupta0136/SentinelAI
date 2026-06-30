"""QoS profile and engine for managing per-class service policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from network_simulation.topology.links import Link
from network_simulation.utils.constants import LinkStatus


@dataclass
class QoSProfile:
    """A QoS service-policy template applied to a traffic class.

    Attributes:
        name: Policy name.
        priority: Scheduling priority (higher = better).
        bandwidth_guarantee_fraction: Fraction of link BW guaranteed.
        latency_bound_ms: Maximum acceptable one-way latency.
        drop_precedence: Drop probability under congestion (0–1).
    """

    name: str
    priority: int = 1
    bandwidth_guarantee_fraction: float = 0.25
    latency_bound_ms: float = 100.0
    drop_precedence: float = 0.5

    def __post_init__(self) -> None:
        """Validate range constraints after initialisation."""
        self.bandwidth_guarantee_fraction = max(
            0.0, min(1.0, self.bandwidth_guarantee_fraction)
        )
        self.drop_precedence = max(0.0, min(1.0, self.drop_precedence))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary of QoS profile fields.
        """
        return {
            "name": self.name,
            "priority": self.priority,
            "bandwidth_guarantee_fraction": self.bandwidth_guarantee_fraction,
            "latency_bound_ms": self.latency_bound_ms,
            "drop_precedence": self.drop_precedence,
        }


class QoSEngine:
    """Manages QoS profiles and applies them to links.

    Provides methods to query the effective bandwidth and latency
    characteristics of a link under configured QoS policies.
    """

    def __init__(self) -> None:
        """Initialise the QoS engine with an empty set of profiles."""
        self._profiles: Dict[str, QoSProfile] = {}

    def register_profile(self, profile: QoSProfile) -> None:
        """Register a QoS profile.

        Args:
            profile: The QoSProfile to register.
        """
        self._profiles[profile.name] = profile

    def get_profile(self, name: str) -> Optional[QoSProfile]:
        """Get a registered QoS profile by name.

        Args:
            name: Profile name.

        Returns:
            The QoSProfile if found, else None.
        """
        return self._profiles.get(name)

    def effective_bandwidth(
        self, link: Link, profile_name: Optional[str] = None
    ) -> float:
        """Return the effective bandwidth for a given link and QoS profile.

        If a profile is specified, the result is the link bandwidth
        multiplied by that profile's guarantee fraction.

        Args:
            link: The link to evaluate.
            profile_name: Optional QoS profile name.

        Returns:
            Effective bandwidth in Mbps.
        """
        if profile_name and profile_name in self._profiles:
            fraction = self._profiles[profile_name].bandwidth_guarantee_fraction
            return link.bandwidth_mbps * fraction
        return link.bandwidth_mbps

    def is_latency_within_bound(
        self, link: Link, profile_name: str
    ) -> bool:
        """Check if a link's latency is within the QoS bound for a profile.

        Args:
            link: The link to evaluate.
            profile_name: Name of the QoS profile.

        Returns:
            True if link latency is within the profile's bound.
        """
        profile = self._profiles.get(profile_name)
        if profile is None:
            return True
        return link.latency_ms <= profile.latency_bound_ms

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all registered profiles.

        Returns:
            Dictionary of QoS profile names to their state.
        """
        return {
            name: profile.to_dict() for name, profile in self._profiles.items()
        }
