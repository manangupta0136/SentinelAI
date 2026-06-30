"""Tunnel degradation injector.

Degrades IPSec/GRE tunnel performance by increasing latency, jitter,
and packet loss, and reducing throughput.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.links import Tunnel
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class TunnelFailureInjector(FaultInjector):
    """Injects tunnel degradation by degrading tunnel metrics.

    Operates on the tunnel objects stored in NetworkBuilder.tunnels.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the tunnel failure injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._baselines: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply tunnel degradation.

        Args:
            fault: The tunnel failure fault event.
        """
        for device_name in fault.affected_devices:
            for tun_name, tunnel in self._network.tunnels.items():
                if (
                    tunnel.source != device_name
                    and tunnel.target != device_name
                ):
                    continue
                if tun_name not in self._baselines:
                    self._baselines[tun_name] = {
                        "latency": tunnel.latency_ms,
                        "jitter": tunnel.jitter_ms,
                        "loss": tunnel.packet_loss,
                        "throughput": tunnel.throughput_mbps,
                    }
                tunnel.status = LinkStatus.DEGRADED
                tunnel.latency_ms = (
                    self._baselines[tun_name]["latency"]
                    * fault.params.get("latency_increase_range", 2.0)
                )
                tunnel.jitter_ms = (
                    self._baselines[tun_name]["jitter"]
                    * fault.params.get("jitter_increase_range", 3.0)
                )
                tunnel.packet_loss = min(
                    0.5,
                    self._baselines[tun_name]["loss"]
                    + fault.params.get("loss_increase_range", 0.01),
                )
                throughput_reduction = fault.params.get(
                    "throughput_reduction_range", 0.3
                )
                tunnel.throughput_mbps = (
                    self._baselines[tun_name]["throughput"]
                    * (1.0 - throughput_reduction)
                )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore tunnels to their pre-failure baselines.

        Args:
            fault: The fault to recover from.
        """
        for tun_name, bl in self._baselines.items():
            tunnel = self._network.tunnels.get(tun_name)
            if tunnel is not None:
                tunnel.latency_ms = bl["latency"]
                tunnel.jitter_ms = bl["jitter"]
                tunnel.packet_loss = bl["loss"]
                tunnel.throughput_mbps = bl["throughput"]
                tunnel.status = LinkStatus.UP
        self._baselines.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with baseline count.
        """
        return {
            "injector": "tunnel_failure",
            "active_baselines": len(self._baselines),
        }
