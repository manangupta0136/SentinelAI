"""Ground truth label dataclass for fault events.

Every injected fault automatically generates a GroundTruthLabel that
records the fault type, affected components, timing, severity, and
expected impact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GroundTruthLabel:
    """A ground-truth label for a single fault event.

    Attributes:
        event_id: Unique event identifier.
        fault_type: Type of fault.
        device: Primary affected device name.
        severity: Fault severity (0–1).
        start_time: ISO 8601 timestamp of fault injection.
        end_time: ISO 8601 timestamp of fault recovery.
        recovery_time: ISO 8601 timestamp when full recovery occurred.
        affected_services: List of affected application services.
        affected_links: List of affected link IDs.
        expected_impact: Human-readable description of expected impact.
    """

    event_id: str = ""
    fault_type: str = ""
    device: str = ""
    severity: float = 0.0
    start_time: str = ""
    end_time: str = ""
    recovery_time: str = ""
    affected_services: List[str] = field(default_factory=list)
    affected_links: List[str] = field(default_factory=list)
    expected_impact: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the label to a dictionary.

        Returns:
            Dictionary of all label fields.
        """
        return {
            "event_id": self.event_id,
            "fault_type": self.fault_type,
            "device": self.device,
            "severity": round(self.severity, 4),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "recovery_time": self.recovery_time,
            "affected_services": ",".join(self.affected_services),
            "affected_links": ",".join(self.affected_links),
            "expected_impact": self.expected_impact,
        }
