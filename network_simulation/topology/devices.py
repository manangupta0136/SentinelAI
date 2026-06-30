"""Device dataclass representing a network node in the simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Device:
    """Represents a network device with dynamic and static attributes.

    All numeric fields that vary during simulation are initialised from
    configuration and updated each tick via the traffic and fault modules.

    Attributes:
        name: Device hostname.
        role: Device role (datacenter, mpls_hub, branch).
        device_type: Hardware platform identifier.
        location: Geographic location identifier.
        os: Operating system name.
        software_version: Software version string.
        cpu_utilization: Current CPU utilization percentage (0–100).
        cpu_growth_rate: Rate of CPU change per tick (smoothed derivative).
        cpu_temperature: Simulated CPU temperature in Celsius.
        interrupt_rate: Interrupt handling load (interrupts/sec).
        process_count: Number of active processes.
        memory_utilization: Current memory utilization percentage (0–100).
        interface_packet_rate: Aggregate packet rate across interfaces (pps).
        routing_table: Routing table mapping destination prefixes to next hops.
        connected_links: List of link IDs connected to this device.
        base_cpu: Baseline CPU utilization (no load).
        base_memory: Baseline memory utilization (no load).
        base_process_count: Baseline process count.
        base_interrupt_rate: Baseline interrupt rate.
        cpu_temp_alpha: Coefficient mapping cpu_utilization -> temp rise.
        memory_gamma_process: Coefficient mapping process_count -> memory.
        memory_gamma_cpu: Coefficient mapping cpu_utilization -> memory.
        interrupt_beta: Coefficient mapping packet_rate -> interrupt_rate.
    """

    name: str
    role: str
    device_type: str = "unknown"
    location: str = "unknown"
    os: str = "unknown"
    software_version: str = "unknown"

    cpu_utilization: float = 0.0
    cpu_growth_rate: float = 0.0
    cpu_temperature: float = 45.0
    interrupt_rate: float = 0.0
    process_count: int = 50
    memory_utilization: float = 0.0
    interface_packet_rate: float = 0.0
    routing_table: Dict[str, str] = field(default_factory=dict)
    connected_links: List[str] = field(default_factory=list)

    base_cpu: float = 25.0
    base_memory: float = 35.0
    base_process_count: int = 55
    base_interrupt_rate: float = 2000.0
    cpu_temp_alpha: float = 2.5
    memory_gamma_process: float = 0.10
    memory_gamma_cpu: float = 0.06
    interrupt_beta: float = 0.005

    def to_dict(self) -> Dict[str, Any]:
        """Serialize device state to a dictionary.

        Returns:
            Dictionary of current device metrics.
        """
        return {
            "device_name": self.name,
            "role": self.role,
            "device_type": self.device_type,
            "location": self.location,
            "cpu_utilization": round(self.cpu_utilization, 2),
            "cpu_growth_rate": round(self.cpu_growth_rate, 4),
            "cpu_temperature": round(self.cpu_temperature, 2),
            "interrupt_rate": round(self.interrupt_rate, 2),
            "process_count": self.process_count,
            "memory_utilization": round(self.memory_utilization, 2),
            "interface_packet_rate": round(self.interface_packet_rate, 2),
        }

    def update_correlated_metrics(self) -> None:
        """Update cpu_temperature, interrupt_rate, and memory_utilization
        based on their correlated drivers.

        These correlation functions make the simulated telemetry explainable
        by providing explicit causal links between primary metrics and their
        derived secondary metrics.

        Relationships:
            - cpu_temperature rises linearly with cpu_utilization.
            - interrupt_rate rises linearly with interface_packet_rate.
            - memory_utilization rises with both process_count and
              cpu_utilization.
        """
        self.cpu_temperature = self.cpu_temp_alpha * self.cpu_utilization + 45.0
        self.interrupt_rate = (
            self.base_interrupt_rate
            + self.interrupt_beta * self.interface_packet_rate
        )
        self.memory_utilization = (
            self.base_memory
            + self.memory_gamma_process * (self.process_count - self.base_process_count)
            + self.memory_gamma_cpu * (self.cpu_utilization - self.base_cpu)
        )
        self.memory_utilization = max(0.0, min(100.0, self.memory_utilization))
        self.cpu_temperature = max(30.0, self.cpu_temperature)
