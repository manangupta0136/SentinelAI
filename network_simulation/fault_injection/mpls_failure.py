"""MPLS underlay degradation injector.

Degrades MPLS LSP (label-switched path) performance by increasing
label-switching delay and degrading LSP throughput.
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


class MplsFailureInjector(FaultInjector):
    """Injects MPLS underlay degradation by degrading MPLS-type links.

    Targets links with type ``mpls_core`` or ``mpls_access``.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the MPLS failure injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._baselines: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply MPLS degradation.

        Args:
            fault: The MPLS failure fault event.
        """
        for link in self._network.get_all_links():
            if link.link_type not in ("mpls_core", "mpls_access"):
                continue
            if (
                link.source not in fault.affected_devices
                and link.target not in fault.affected_devices
            ):
                continue
            if link.link_id not in self._baselines:
                self._baselines[link.link_id] = {
                    "latency": link.latency_ms,
                    "loss": link.packet_loss,
                    "bw": link.bandwidth_mbps,
                }
            link.status = LinkStatus.DEGRADED
            delay_mult = fault.params.get(
                "label_switching_delay_multiplier", 3.0
            )
            link.latency_ms = (
                self._baselines[link.link_id]["latency"] * delay_mult
            )
            degradation = fault.params.get("lsp_degradation", 0.4)
            link.bandwidth_mbps = (
                self._baselines[link.link_id]["bw"] * (1.0 - degradation)
            )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore MPLS links to their baselines.

        Args:
            fault: The fault to recover from.
        """
        for link_id, bl in self._baselines.items():
            link = self._find_link(link_id)
            if link is not None:
                link.latency_ms = bl["latency"]
                link.packet_loss = bl["loss"]
                link.bandwidth_mbps = bl["bw"]
                link.status = LinkStatus.UP
        self._baselines.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with baseline count.
        """
        return {
            "injector": "mpls_failure",
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
