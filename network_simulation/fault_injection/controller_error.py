"""Controller misconfiguration injector.

Simulates SDN controller or orchestration errors that push incorrect
configurations, causing policy violations and intent mismatches.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.devices import Device
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class ControllerErrorInjector(FaultInjector):
    """Injects controller misconfiguration by altering device parameters
    to simulate policy violations or intent mismatches.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the controller error injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._original_configs: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply controller misconfiguration.

        Args:
            fault: The controller error fault event.
        """
        impact = fault.params.get("misconfiguration_impact", 0.3)
        for device_name in fault.affected_devices:
            device = self._get_device(device_name)
            if device is None:
                continue
            if device_name not in self._original_configs:
                self._original_configs[device_name] = {
                    "cpu": device.cpu_utilization,
                    "memory": device.memory_utilization,
                    "process_count": device.process_count,
                }
            device.cpu_utilization = min(
                100.0, device.cpu_utilization * (1.0 + impact)
            )
            device.memory_utilization = min(
                100.0, device.memory_utilization * (1.0 + impact)
            )
            device.process_count = int(
                device.process_count * (1.0 + impact * 0.5)
            )

    def recover(self, fault: ScheduledFault) -> None:
        """Restore devices to their original configurations.

        Args:
            fault: The fault to recover from.
        """
        for device_name, cfg in self._original_configs.items():
            device = self._get_device(device_name)
            if device is not None:
                device.cpu_utilization = cfg["cpu"]
                device.memory_utilization = cfg["memory"]
                device.process_count = int(cfg["process_count"])
        self._original_configs.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with affected device count.
        """
        return {
            "injector": "controller_error",
            "affected_devices": len(self._original_configs),
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
