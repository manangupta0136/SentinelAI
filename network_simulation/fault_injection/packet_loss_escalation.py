"""Packet loss escalation injector.

Simulates escalating packet loss on links, starting from a base increase
and growing at a configurable rate per tick.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.links import Link
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class PacketLossEscalationInjector(FaultInjector):
    """Injects escalating packet loss on affected links.

    Packet loss starts at a base increase and rises each tick,
    simulating a worsening interface or medium issue.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the packet loss escalation injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._baselines: Dict[str, Dict[str, float]] = {}
        self._escalation_step: Dict[str, int] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply or escalate packet loss.

        Args:
            fault: The packet loss escalation fault event.
        """
        loss_base = fault.params.get("loss_base_increase", 0.02)
        loss_rate = fault.params.get("loss_escalation_rate", 0.005)

        for link_id in fault.affected_links:
            link = self._find_link(link_id)
            if link is None:
                continue
            if link_id not in self._baselines:
                self._baselines[link_id] = {
                    "loss": link.packet_loss,
                    "status": link.status,
                }
                self._escalation_step[link_id] = 0
                link.status = LinkStatus.DEGRADED
            step = self._escalation_step.get(link_id, 0)
            link.packet_loss = min(
                0.5,
                self._baselines[link_id]["loss"]
                + loss_base
                + step * loss_rate,
            )
            self._escalation_step[link_id] = step + 1
            if link.packet_loss > 0.2:
                link.status = LinkStatus.DOWN

    def recover(self, fault: ScheduledFault) -> None:
        """Restore links to their pre-escalation baselines.

        Args:
            fault: The fault to recover from.
        """
        for link_id, bl in self._baselines.items():
            link = self._find_link(link_id)
            if link is not None:
                link.packet_loss = bl["loss"]
                link.status = bl["status"]
        self._baselines.clear()
        self._escalation_step.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with baseline count.
        """
        return {
            "injector": "packet_loss_escalation",
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
