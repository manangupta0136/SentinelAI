"""Event logger that maintains ground-truth labels for all fault events.

Records fault start and end events and produces a list of
GroundTruthLabel instances for dataset export.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from network_simulation.labeling.ground_truth import GroundTruthLabel
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)

_SERVICE_MAP: Dict[str, List[str]] = {
    "congestion": ["erp", "web_traffic", "video_conferencing"],
    "bgp_flap": ["erp", "database", "web_traffic"],
    "ospf_failure": ["erp", "database"],
    "tunnel_failure": ["video_conferencing", "erp"],
    "mpls_failure": ["erp", "database", "web_traffic"],
    "link_failure": ["erp", "database", "web_traffic", "video_conferencing"],
    "controller_error": ["erp", "database"],
    "cpu_overload": ["erp", "database", "video_conferencing"],
    "memory_exhaustion": ["erp", "database"],
    "packet_loss_escalation": ["video_conferencing", "web_traffic"],
}

_IMPACT_MAP: Dict[str, str] = {
    "congestion": "Increased latency and packet loss on affected links",
    "bgp_flap": "Routing instability causing intermittent connectivity",
    "ospf_failure": "OSPF reconvergence causing temporary blackholing",
    "tunnel_failure": "Tunnel degradation impacting encrypted traffic",
    "mpls_failure": "MPLS LSP degradation impacting label-switched traffic",
    "link_failure": "Complete link outage requiring failover",
    "controller_error": "Policy violations causing incorrect traffic engineering",
    "cpu_overload": "Device CPU saturation causing control plane issues",
    "memory_exhaustion": "Memory pressure causing process restarts",
    "packet_loss_escalation": "Escalating packet loss degrading application QoE",
}


class EventLogger:
    """Tracks fault start and end events and builds GroundTruthLabel instances."""

    def __init__(self) -> None:
        """Initialise the event logger."""
        self._active_events: Dict[str, ScheduledFault] = {}
        self._labels: List[GroundTruthLabel] = []
        self._start_times: Dict[str, str] = {}

    def log_fault_start(
        self, fault: ScheduledFault, timestamp: str
    ) -> None:
        """Record the start of a fault event.

        Args:
            fault: The scheduled fault that started.
            timestamp: ISO 8601 start timestamp.
        """
        self._active_events[fault.event_id] = fault
        self._start_times[fault.event_id] = timestamp
        logger.debug(
            "Fault start: %s type=%s devices=%s",
            fault.event_id,
            fault.fault_type,
            fault.affected_devices,
        )

    def log_fault_end(
        self, fault: ScheduledFault, timestamp: str
    ) -> None:
        """Record the end of a fault event and create a label.

        Args:
            fault: The scheduled fault that ended.
            timestamp: ISO 8601 end timestamp.
        """
        start_time = self._start_times.get(fault.event_id, "")
        label = GroundTruthLabel(
            event_id=fault.event_id,
            fault_type=fault.fault_type,
            device=fault.affected_devices[0]
            if fault.affected_devices
            else "",
            severity=fault.severity,
            start_time=start_time,
            end_time=timestamp,
            recovery_time=timestamp,
            affected_services=_SERVICE_MAP.get(
                fault.fault_type, ["unknown"]
            ),
            affected_links=list(fault.affected_links),
            expected_impact=_IMPACT_MAP.get(
                fault.fault_type, "Unknown impact"
            ),
        )
        self._labels.append(label)
        self._active_events.pop(fault.event_id, None)
        logger.debug("Fault end: %s type=%s", fault.event_id, fault.fault_type)

    def get_labels(self) -> List[GroundTruthLabel]:
        """Return all completed ground-truth labels.

        Returns:
            List of GroundTruthLabel instances.
        """
        return list(self._labels)

    def get_active_events(self) -> Dict[str, ScheduledFault]:
        """Return currently active fault events.

        Returns:
            Dict mapping event_id to ScheduledFault.
        """
        return dict(self._active_events)
