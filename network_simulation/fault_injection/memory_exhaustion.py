"""Memory exhaustion injector.

Simulates memory leaks by increasing memory_utilization and process_count
together, consistent with the correlation functions in the Device model.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.devices import Device
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryExhaustionInjector(FaultInjector):
    """Injects memory exhaustion on affected devices.

    Increases memory_utilization and process_count together, simulating a
    memory leak.  The correlation between the two is intentional: a
    process leak drives memory up, which is exactly the causal link we
    want labels to capture.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the memory exhaustion injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._originals: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply memory exhaustion.

        Args:
            fault: The memory exhaustion fault event.
        """
        mem_increase = fault.params.get("memory_increase_range", 30.0)
        process_leak = int(
            fault.params.get("process_leak_count", 50)
        )

        for device_name in fault.affected_devices:
            device = self._get_device(device_name)
            if device is None:
                continue
            if device_name not in self._originals:
                self._originals[device_name] = {
                    "memory": device.memory_utilization,
                    "process": device.process_count,
                }
            device.memory_utilization = min(
                100.0, device.memory_utilization + mem_increase
            )
            device.process_count += process_leak

    def recover(self, fault: ScheduledFault) -> None:
        """Restore devices to pre-exhaustion baselines.

        Args:
            fault: The fault to recover from.
        """
        for device_name, orig in self._originals.items():
            device = self._get_device(device_name)
            if device is not None:
                device.memory_utilization = orig["memory"]
                device.process_count = int(orig["process"])
        self._originals.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with affected device count.
        """
        return {
            "injector": "memory_exhaustion",
            "affected_devices": len(self._originals),
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
