"""Simplified routing engine for the simulated network.

Computes shortest-path routing tables using link latency as the metric
and injects BGP/OSPF event counters for telemetry.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from network_simulation.topology.devices import Device
from network_simulation.topology.links import Link
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class RoutingEngine:
    """Computes and maintains routing tables for all devices.

    Uses shortest-path (Dijkstra) over link latency.  Also maintains
    counters for BGP and OSPF events that can be reported as telemetry.
    """

    def __init__(self, graph: nx.DiGraph) -> None:
        """Initialise the routing engine.

        Args:
            graph: NetworkX directed graph whose edges carry ``link``
                attributes of type :class:`~topology.links.Link`.
        """
        self._graph = graph
        self.bgp_events: int = 0
        self.ospf_events: int = 0
        self.route_changes: int = 0
        self._last_route_hash: Optional[int] = None

    def recompute_all(self) -> None:
        """Recompute routing tables for every device in the topology."""
        nodes = list(self._graph.nodes())
        if not nodes:
            return
        new_hash = hash(tuple(nodes))
        for src in nodes:
            self._compute_routing_table(src)
        if self._last_route_hash is not None and new_hash != self._last_route_hash:
            self.route_changes += 1
        self._last_route_hash = new_hash

    def _compute_routing_table(self, source: str) -> None:
        """Compute the routing table for a single source device.

        Uses Dijkstra with link latency as the weight.  Links with
        DOWN status are excluded.

        Args:
            source: Source device name.
        """
        device: Device = self._graph.nodes[source]["device"]
        device.routing_table = {}

        try:
            distances, paths = nx.single_source_dijkstra(
                self._graph, source, weight=self._link_weight
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return

        for target in paths:
            if target == source:
                continue
            path = paths[target]
            next_hop = path[1] if len(path) > 1 else target
            prefix = f"10.{hash(target) % 256}.0.0/16"
            device.routing_table[prefix] = next_hop

    def _link_weight(self, u: str, v: str, data: Dict[str, Any]) -> float:
        """Return the latency weight for an edge, or infinity if DOWN.

        Args:
            u: Source node.
            v: Target node.
            data: Edge data dictionary.

        Returns:
            Latency in milliseconds, or infinity if the link is down.
        """
        link: Link = data["link"]
        if link.status == LinkStatus.DOWN:
            return float("inf")
        return link.latency_ms

    def trigger_bgp_event(self) -> None:
        """Record a BGP event (e.g. route withdrawal or flap)."""
        self.bgp_events += 1

    def trigger_ospf_event(self) -> None:
        """Record an OSPF event (e.g. LSA flood or adjacency change)."""
        self.ospf_events += 1

    def reset_counters(self) -> None:
        """Reset BGP, OSPF, and route-change counters."""
        self.bgp_events = 0
        self.ospf_events = 0
        self.route_changes = 0

    def to_dict(self) -> Dict[str, Any]:
        """Return routing engine state summary.

        Returns:
            Dictionary of event counters.
        """
        return {
            "bgp_events": self.bgp_events,
            "ospf_events": self.ospf_events,
            "route_changes": self.route_changes,
        }
