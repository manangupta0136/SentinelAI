"""BGP route flapping injector.

Simulates BGP route instability by repeatedly withdrawing and
re-advertising prefixes, causing routing table churn.
"""

from __future__ import annotations

from typing import Any, Dict, List

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.devices import Device
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class BgpFlapInjector(FaultInjector):
    """Injects BGP route flapping on affected devices.

    Each tick, randomly removes and re-adds routing table entries,
    simulating prefix withdrawal and re-advertisement cycles.
    """

    def __init__(
        self,
        network_builder: NetworkBuilder,
        routing_engine: RoutingEngine,
    ) -> None:
        """Initialise the BGP flap injector.

        Args:
            network_builder: Network topology access.
            routing_engine: Routing engine to trigger BGP events.
        """
        self._network = network_builder
        self._routing = routing_engine
        self._withdrawn_prefixes: Dict[str, List[str]] = {}
        self._flap_count: int = 0

    def apply(self, fault: ScheduledFault) -> None:
        """Apply BGP route flapping.

        Args:
            fault: The BGP flap fault event.
        """
        self._routing.trigger_bgp_event()
        self._flap_count += 1
        for device_name in fault.affected_devices:
            device = self._get_device(device_name)
            if device is None:
                continue
            if device_name not in self._withdrawn_prefixes:
                self._withdrawn_prefixes[device_name] = []
            prefixes = list(device.routing_table.keys())
            if not prefixes:
                continue
            import numpy as np
            rng = np.random.default_rng()
            withdrawal_rate = fault.params.get(
                "prefix_withdrawal_rate", 0.3
            )
            num_withdraw = max(1, int(len(prefixes) * withdrawal_rate))
            to_withdraw = list(
                rng.choice(prefixes, size=num_withdraw, replace=False)
            )
            for prefix in to_withdraw:
                self._withdrawn_prefixes[device_name].append(
                    device.routing_table.pop(prefix, "")
                )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore withdrawn prefixes to routing tables.

        Args:
            fault: The fault to recover from.
        """
        for device_name, prefixes in self._withdrawn_prefixes.items():
            device = self._get_device(device_name)
            if device is None:
                continue
            for i, prefix in enumerate(prefixes):
                key = f"10.{hash(prefix) % 256}.0.0/16"
                device.routing_table[key] = prefix
        self._withdrawn_prefixes.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with flap count and active withdrawals.
        """
        return {
            "injector": "bgp_flap",
            "flap_count": self._flap_count,
            "active_withdrawals": sum(
                len(v) for v in self._withdrawn_prefixes.values()
            ),
        }

    def _get_device(self, name: str) -> Device:
        """Get a device by name.

        Args:
            name: Device name.

        Returns:
            Device or None.
        """
        try:
            return self._network.get_device(name)
        except KeyError:
            return None
