"""CPU overload injector.

Simulates CPU overload by increasing cpu_utilization, cpu_growth_rate,
cpu_temperature, and interrupt_rate together, consistent with the
correlation functions in the Device model.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.devices import Device
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class CpuOverloadInjector(FaultInjector):
    """Injects CPU overload on affected devices.

    Manipulates cpu_utilization, cpu_growth_rate, cpu_temperature, and
    interrupt_rate together, maintaining consistency with the correlation
    functions defined in Device.update_correlated_metrics().
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the CPU overload injector.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder
        self._originals: Dict[str, Dict[str, float]] = {}

    def apply(self, fault: ScheduledFault) -> None:
        """Apply CPU overload.

        Args:
            fault: The CPU overload fault event.
        """
        cpu_increase = fault.params.get("cpu_increase_range", 40.0)
        temp_coeff = fault.params.get("temp_increase_coefficient", 2.0)
        process_spike = int(
            fault.params.get("process_spike_count", 80)
        )
        interrupt_spike = fault.params.get(
            "interrupt_spike_rate", 5000.0
        )

        for device_name in fault.affected_devices:
            device = self._get_device(device_name)
            if device is None:
                continue
            if device_name not in self._originals:
                self._originals[device_name] = {
                    "cpu": device.cpu_utilization,
                    "growth": device.cpu_growth_rate,
                    "temp": device.cpu_temperature,
                    "interrupt": device.interrupt_rate,
                    "process": device.process_count,
                }
            device.cpu_utilization = min(
                100.0, device.cpu_utilization + cpu_increase
            )
            device.cpu_growth_rate = cpu_increase / 10.0
            device.cpu_temperature = (
                45.0 + temp_coeff * device.cpu_utilization
            )
            device.interrupt_rate += interrupt_spike
            device.process_count += process_spike

    def recover(self, fault: ScheduledFault) -> None:
        """Restore devices to pre-overload baselines.

        Args:
            fault: The fault to recover from.
        """
        for device_name, orig in self._originals.items():
            device = self._get_device(device_name)
            if device is not None:
                device.cpu_utilization = orig["cpu"]
                device.cpu_growth_rate = orig["growth"]
                device.cpu_temperature = orig["temp"]
                device.interrupt_rate = orig["interrupt"]
                device.process_count = int(orig["process"])
        self._originals.clear()

    def serialize(self) -> Dict[str, Any]:
        """Return injector state.

        Returns:
            Dictionary with affected device count.
        """
        return {
            "injector": "cpu_overload",
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
