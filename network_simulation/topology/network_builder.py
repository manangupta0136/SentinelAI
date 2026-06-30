"""Builds a NetworkX directed graph from YAML configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from network_simulation.topology.devices import Device
from network_simulation.topology.links import Link, Tunnel
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.helpers import load_yaml_config
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkBuilder:
    """Constructs and holds the network topology as a NetworkX DiGraph.

    Nodes represent devices (with a ``device`` attribute of type
    :class:`~topology.devices.Device`).  Edges represent links (with a
    ``link`` attribute of type :class:`~topology.links.Link`).  Tunnels
    are stored as a separate list and linked to their underlying edges
    by a ``tunnels`` dict keyed by tunnel name.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialise the builder.

        Args:
            config_path: Path to network.yaml.  If None the graph is empty.
        """
        self.graph: nx.DiGraph = nx.DiGraph()
        self.tunnels: Dict[str, Tunnel] = {}
        self._config: Dict[str, Any] = {}
        if config_path is not None:
            self._config = load_yaml_config(config_path)
            self._build()

    def _build(self) -> None:
        """Construct the full topology from the loaded configuration."""
        self._add_devices()
        self._add_links()
        self._add_tunnels()
        logger.info(
            "Network built: %d devices, %d links, %d tunnels",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
            len(self.tunnels),
        )

    def _add_devices(self) -> None:
        """Add device nodes from config to the graph."""
        topology = self._config.get("topology", {})
        for node_cfg in topology.get("nodes", []):
            device = Device(
                name=node_cfg["name"],
                role=node_cfg["role"],
                device_type=node_cfg.get("device_type", "unknown"),
                location=node_cfg.get("location", "unknown"),
                os=node_cfg.get("os", "unknown"),
                software_version=node_cfg.get("software_version", "unknown"),
                cpu_utilization=node_cfg.get("base_cpu", 25.0),
                cpu_growth_rate=0.0,
                cpu_temperature=45.0,
                interrupt_rate=node_cfg.get("base_interrupt_rate", 2000.0),
                process_count=node_cfg.get("base_process_count", 55),
                memory_utilization=node_cfg.get("base_memory", 35.0),
                interface_packet_rate=0.0,
                base_cpu=node_cfg.get("base_cpu", 25.0),
                base_memory=node_cfg.get("base_memory", 35.0),
                base_process_count=node_cfg.get("base_process_count", 55),
                base_interrupt_rate=node_cfg.get("base_interrupt_rate", 2000.0),
                cpu_temp_alpha=node_cfg.get("cpu_temp_alpha", 2.5),
                memory_gamma_process=node_cfg.get("memory_gamma_process", 0.10),
                memory_gamma_cpu=node_cfg.get("memory_gamma_cpu", 0.06),
                interrupt_beta=node_cfg.get("interrupt_beta", 0.005),
            )
            self.graph.add_node(device.name, device=device)

    def _add_links(self) -> None:
        """Add link edges from config to the graph."""
        topology = self._config.get("topology", {})
        for link_cfg in topology.get("links", []):
            source = link_cfg["source"]
            target = link_cfg["target"]
            link_id = f"{source}_to_{target}"
            link = Link(
                link_id=link_id,
                source=source,
                target=target,
                link_type=link_cfg.get("type", "mpls_access"),
                status=LinkStatus.UP,
                bandwidth_mbps=link_cfg.get("bandwidth_mbps", 1000.0),
                latency_ms=link_cfg.get("base_latency_ms", 10.0),
                base_latency_ms=link_cfg.get("base_latency_ms", 10.0),
                jitter_ms=link_cfg.get("base_jitter_ms", 0.5),
                base_jitter_ms=link_cfg.get("base_jitter_ms", 0.5),
                packet_loss=link_cfg.get("base_packet_loss", 0.001),
                base_packet_loss=link_cfg.get("base_packet_loss", 0.001),
                mtu=link_cfg.get("mtu", 1500),
            )
            self.graph.add_edge(source, target, link=link)
            self._register_link_on_devices(link)

    def _add_tunnels(self) -> None:
        """Add tunnel objects from config."""
        topology = self._config.get("topology", {})
        for tun_cfg in topology.get("tunnels", []):
            tunnel = Tunnel(
                name=tun_cfg["name"],
                source=tun_cfg["source"],
                target=tun_cfg["target"],
                tunnel_type=tun_cfg.get("type", "ipsec"),
                status=LinkStatus.UP,
                latency_ms=tun_cfg.get("base_latency_ms", 10.0),
                base_latency_ms=tun_cfg.get("base_latency_ms", 10.0),
                jitter_ms=tun_cfg.get("base_jitter_ms", 1.0),
                base_jitter_ms=tun_cfg.get("base_jitter_ms", 1.0),
                packet_loss=tun_cfg.get("base_packet_loss", 0.001),
                base_packet_loss=tun_cfg.get("base_packet_loss", 0.001),
            )
            self.tunnels[tunnel.name] = tunnel

    def _register_link_on_devices(self, link: Link) -> None:
        """Add the link ID to the connected_links list on both endpoint devices.

        Args:
            link: The link to register.
        """
        for dev_name in (link.source, link.target):
            if self.graph.has_node(dev_name):
                device: Device = self.graph.nodes[dev_name]["device"]
                if link.link_id not in device.connected_links:
                    device.connected_links.append(link.link_id)

    def get_device(self, name: str) -> Device:
        """Get a device by name.

        Args:
            name: Device name.

        Returns:
            The Device dataclass instance.

        Raises:
            KeyError: If the device does not exist.
        """
        return self.graph.nodes[name]["device"]

    def get_link(self, source: str, target: str) -> Link:
        """Get a link between two devices.

        Args:
            source: Source device name.
            target: Target device name.

        Returns:
            The Link dataclass instance.

        Raises:
            KeyError: If no edge exists.
        """
        return self.graph.edges[source, target]["link"]

    def get_all_devices(self) -> List[Device]:
        """Return all device instances in the topology.

        Returns:
            List of Device objects.
        """
        return [data["device"] for _, data in self.graph.nodes(data=True)]

    def get_all_links(self) -> List[Link]:
        """Return all link instances in the topology.

        Returns:
            List of Link objects.
        """
        return [data["link"] for _, _, data in self.graph.edges(data=True)]

    def get_tunnel(self, name: str) -> Tunnel:
        """Get a tunnel by name.

        Args:
            name: Tunnel name.

        Returns:
            The Tunnel dataclass instance.

        Raises:
            KeyError: If the tunnel does not exist.
        """
        if name not in self.tunnels:
            raise KeyError(f"Tunnel not found: {name}")
        return self.tunnels[name]

    def get_devices_by_role(self, role: str) -> List[Device]:
        """Get all devices matching a given role.

        Args:
            role: Device role string.

        Returns:
            List of matching Device objects.
        """
        return [d for d in self.get_all_devices() if d.role == role]

    def links_for_device(self, device_name: str) -> List[Link]:
        """Get all links incident to a device.

        Args:
            device_name: Device name.

        Returns:
            List of Link objects connected to the device.
        """
        result = []
        for u, v, data in self.graph.edges(data=True):
            link: Link = data["link"]
            if u == device_name or v == device_name:
                result.append(link)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the full topology to a dictionary.

        Returns:
            Dictionary with devices, links, and tunnels.
        """
        return {
            "devices": [d.to_dict() for d in self.get_all_devices()],
            "links": [l.to_dict() for l in self.get_all_links()],
            "tunnels": [t.to_dict() for t in self.tunnels.values()],
        }
