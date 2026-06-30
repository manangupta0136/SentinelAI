"""Link and Tunnel dataclasses for network topology edges."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from network_simulation.utils.constants import LinkStatus


@dataclass
class Link:
    """Represents a physical or logical network link.

    Attributes:
        link_id: Unique link identifier (e.g. "mpls-hub-1_to_branch-1").
        source: Source device name.
        target: Target device name.
        link_type: Type of link (mpls_core, mpls_access, sdwan_overlay).
        status: Current operational status (UP, DEGRADED, DOWN).
        bandwidth_mbps: Link bandwidth capacity.
        latency_ms: Current one-way latency in milliseconds.
        base_latency_ms: Baseline latency under no load.
        jitter_ms: Current jitter in milliseconds.
        base_jitter_ms: Baseline jitter.
        packet_loss: Current packet loss fraction (0–1).
        base_packet_loss: Baseline packet loss fraction.
        utilization: Current bandwidth utilization fraction (0–1).
        queue_length: Current queue depth in packets.
        mtu: Maximum transmission unit in bytes.
        interface_errors: Count of interface errors this tick.
        is_tunnel: Whether this link represents a tunnel.
        tunnel_name: Tunnel name if this is a tunnel link.
    """

    link_id: str
    source: str
    target: str
    link_type: str = "mpls_access"
    status: str = LinkStatus.UP
    bandwidth_mbps: float = 1000.0
    latency_ms: float = 10.0
    base_latency_ms: float = 10.0
    jitter_ms: float = 0.5
    base_jitter_ms: float = 0.5
    packet_loss: float = 0.001
    base_packet_loss: float = 0.001
    utilization: float = 0.0
    queue_length: int = 0
    mtu: int = 1500
    interface_errors: int = 0
    is_tunnel: bool = False
    tunnel_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize link state to a dictionary.

        Returns:
            Dictionary of current link metrics.
        """
        return {
            "link_id": self.link_id,
            "source": self.source,
            "target": self.target,
            "link_type": self.link_type,
            "status": self.status,
            "bandwidth_mbps": self.bandwidth_mbps,
            "latency_ms": round(self.latency_ms, 3),
            "jitter_ms": round(self.jitter_ms, 3),
            "packet_loss": round(self.packet_loss, 6),
            "utilization": round(self.utilization, 4),
            "queue_length": self.queue_length,
            "mtu": self.mtu,
            "interface_errors": self.interface_errors,
        }


@dataclass
class Tunnel:
    """Represents an IPSec tunnel overlay on the physical topology.

    Attributes:
        name: Tunnel name.
        source: Source device name.
        target: Target device name.
        tunnel_type: Tunnel technology (ipsec, gre, vxlan).
        status: Current operational status.
        latency_ms: Current tunnel latency.
        base_latency_ms: Baseline tunnel latency.
        jitter_ms: Current tunnel jitter.
        base_jitter_ms: Baseline tunnel jitter.
        packet_loss: Current tunnel packet loss.
        base_packet_loss: Baseline tunnel packet loss.
        throughput_mbps: Current tunnel throughput.
        utilization: Bandwidth utilization fraction.
    """

    name: str
    source: str
    target: str
    tunnel_type: str = "ipsec"
    status: str = LinkStatus.UP
    latency_ms: float = 10.0
    base_latency_ms: float = 10.0
    jitter_ms: float = 1.0
    base_jitter_ms: float = 1.0
    packet_loss: float = 0.001
    base_packet_loss: float = 0.001
    throughput_mbps: float = 0.0
    utilization: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tunnel state to a dictionary.

        Returns:
            Dictionary of current tunnel metrics.
        """
        return {
            "tunnel_name": self.name,
            "source": self.source,
            "target": self.target,
            "tunnel_type": self.tunnel_type,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 3),
            "jitter_ms": round(self.jitter_ms, 3),
            "packet_loss": round(self.packet_loss, 6),
            "throughput_mbps": round(self.throughput_mbps, 2),
            "utilization": round(self.utilization, 4),
        }
