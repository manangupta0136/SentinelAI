"""OSPF instability injector.

Simulates OSPF link-state advertisement flooding and adjacency
flapping, causing SPF recalculations and route instability.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class OspfFailureInjector(FaultInjector):
    """Injects OSPF instability by generating LSA events and random
    link status transitions that trigger SPF recalculations.
    """

    def __init__(
        self,
        network_builder: NetworkBuilder,
        routing_engine: RoutingEngine,
    ) -> None:
        """Initialise the OSPF failure injector.

        Args:
            network_builder: Network topology access.
            routing_engine: Routing engine to trigger OSPF events.
        """
        self._network = network_builder
        self._routing = routing_engine
        self._original_status: Dict[str, str] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply OSPF instability.

        Args:
            fault: The OSPF failure fault event.
        """
        self._routing.trigger_ospf_event()
        for link_id in fault.affected_links:
            link = self._find_link(link_id)
            if link is None:
                continue
            if link.link_id not in self._original_status:
                self._original_status[link.link_id] = link.status
            import numpy as np
            rng = np.random.default_rng()
            if rng.uniform() < fault.params.get(
                "adjacency_flap_probability", 0.2
            ):
                link.status = "DEGRADED"
                link.latency_ms *= fault.params.get(
                    "spf_interval_multiplier", 2.0
                )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore original link statuses.

        Args:
            fault: The fault to recover from.
        """
        for link_id, status in self._original_status.items():
            link = self._find_link(link_id)
            if link is not None:
                link.status = status
        self._original_status.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with affected link count.
        """
        return {
            "injector": "ospf_failure",
            "affected_links": len(self._original_status),
        }

    def _find_link(self, link_id: str) -> Any:
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
