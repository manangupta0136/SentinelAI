"""Progressive congestion injector.

Gradually increases latency, jitter, packet loss, and reduces effective
bandwidth on affected links to simulate network congestion.
"""

from __future__ import annotations

from typing import Any, Dict, List

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.links import Link
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class CongestionInjector(FaultInjector):
    """Injects progressive congestion on specified links.

    Congestion degrades links incrementally: each tick increases latency,
    jitter, and packet loss while reducing effective bandwidth.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._baselines: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply or escalate congestion on affected links.

        Args:
            fault: The congestion fault event.
        """
        for link_id in fault.affected_links:
            link = self._find_link(link_id)
            if link is None:
                continue
            if link.link_id not in self._baselines:
                self._baselines[link.link_id] = {
                    "latency": link.latency_ms,
                    "jitter": link.jitter_ms,
                    "loss": link.packet_loss,
                    "bw": link.bandwidth_mbps,
                }
                link.status = LinkStatus.DEGRADED
            severity = fault.severity
            bw_reduction = fault.params.get(
                "bandwidth_reduction_range", severity
            )
            link.bandwidth_mbps = (
                self._baselines[link.link_id]["bw"] * (1.0 - bw_reduction)
            )
            lat_mult = fault.params.get(
                "latency_multiplier_range", 1.0 + severity * 3.0
            )
            link.latency_ms = (
                self._baselines[link.link_id]["latency"] * lat_mult
            )
            jit_mult = fault.params.get(
                "jitter_multiplier_range", 1.0 + severity * 5.0
            )
            link.jitter_ms = (
                self._baselines[link.link_id]["jitter"] * jit_mult
            )
            loss_inc = fault.params.get(
                "loss_increase_range", severity * 0.01
            )
            link.packet_loss = min(
                0.5,
                self._baselines[link.link_id]["loss"] + loss_inc,
            )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore links to their pre-congestion baselines.

        Args:
            fault: The fault to recover from.
        """
        for link_id in fault.affected_links:
            if link_id in self._baselines:
                bl = self._baselines[link_id]
                link = self._find_link(link_id)
                if link is not None:
                    link.latency_ms = bl["latency"]
                    link.jitter_ms = bl["jitter"]
                    link.packet_loss = bl["loss"]
                    link.bandwidth_mbps = bl["bw"]
                    link.status = LinkStatus.UP
                del self._baselines[link_id]

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with baseline count.
        """
        return {
            "injector": "congestion",
            "active_baselines": len(self._baselines),
        }

    def _find_link(self, link_id: str) -> Link:
        """Find a link by its link_id.

        Args:
            link_id: Link identifier.

        Returns:
            The Link object or None.
        """
        for link in self._network.get_all_links():
            if link.link_id == link_id:
                return link
        return None
