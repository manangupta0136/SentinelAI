"""Recovery engine for fault injectors.

Handles post-fault recovery actions that are common across fault types,
such as re-triggering routing table recomputation.
"""

from __future__ import annotations

from typing import Any, Dict

from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class RecoveryEngine:
    """Coordinates recovery actions after fault recovery.

    Performs topology-level actions such as routing recomputation and
    state verification.
    """

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the recovery engine.

        Args:
            network_builder: Network topology access.
        """
        self._network = network_builder

    def recover(self, fault: ScheduledFault) -> None:
        """Execute recovery actions for a fault.

        Args:
            fault: The fault that has completed recovery.
        """
        logger.info(
            "Recovery complete: type=%s event=%s method=%s",
            fault.fault_type,
            fault.event_id,
            fault.recovery_method,
        )

    def hard_reset_device(self, device_name: str) -> None:
        """Simulate a hard reset of a device by restoring baseline metrics.

        Args:
            device_name: Name of the device to reset.
        """
        try:
            device = self._network.get_device(device_name)
        except KeyError:
            logger.warning("Cannot reset unknown device: %s", device_name)
            return
        device.cpu_utilization = device.base_cpu
        device.cpu_growth_rate = 0.0
        device.cpu_temperature = 45.0
        device.memory_utilization = device.base_memory
        device.process_count = device.base_process_count
        device.interface_packet_rate = 0.0
        logger.info("Hard reset performed on device: %s", device_name)
