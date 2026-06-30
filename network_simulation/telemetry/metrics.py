"""Telemetry data models for the simulation.

A TelemetryRecord is a single row of telemetry at one tick for one device
or link.  TelemetryFrame is a collection of records backed by a pandas
DataFrame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class TelemetryRecord:
    """A single telemetry observation at one simulation tick.

    Attributes:
        tick: Simulation tick number.
        timestamp: ISO 8601 timestamp string.
        device_name: Device name (or link_id for link metrics).
        record_type: "device" or "link" or "tunnel".
        cpu_utilization: CPU utilization percentage.
        cpu_growth_rate: CPU change rate.
        cpu_temperature: CPU temperature.
        interrupt_rate: Interrupt rate (interrupts/sec).
        process_count: Number of active processes.
        memory_utilization: Memory utilization percentage.
        interface_packet_rate: Packet rate (pps).
        bandwidth_utilization: Link bandwidth utilization fraction.
        throughput_mbps: Throughput in Mbps.
        latency_ms: Latency in milliseconds.
        jitter_ms: Jitter in milliseconds.
        packet_loss: Packet loss fraction.
        queue_occupancy: Queue depth in packets.
        interface_errors: Interface error count.
        bgp_events: BGP event count this tick.
        ospf_events: OSPF event count this tick.
        tunnel_latency_ms: Tunnel latency (for tunnel records).
        tunnel_packet_loss: Tunnel packet loss (for tunnel records).
        tunnel_jitter_ms: Tunnel jitter (for tunnel records).
        route_changes: Route change count this tick.
        link_availability: Link availability (1.0 = up, 0.0 = down).
        link_status: Link status string.
    """

    tick: int
    timestamp: str
    device_name: str = ""
    record_type: str = "device"
    cpu_utilization: float = 0.0
    cpu_growth_rate: float = 0.0
    cpu_temperature: float = 0.0
    interrupt_rate: float = 0.0
    process_count: int = 0
    memory_utilization: float = 0.0
    interface_packet_rate: float = 0.0
    bandwidth_utilization: float = 0.0
    throughput_mbps: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss: float = 0.0
    queue_occupancy: int = 0
    interface_errors: int = 0
    bgp_events: int = 0
    ospf_events: int = 0
    tunnel_latency_ms: float = 0.0
    tunnel_packet_loss: float = 0.0
    tunnel_jitter_ms: float = 0.0
    route_changes: int = 0
    link_availability: float = 1.0
    link_status: str = "UP"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary of all fields.
        """
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "device_name": self.device_name,
            "record_type": self.record_type,
            "cpu_utilization": round(self.cpu_utilization, 2),
            "cpu_growth_rate": round(self.cpu_growth_rate, 4),
            "cpu_temperature": round(self.cpu_temperature, 2),
            "interrupt_rate": round(self.interrupt_rate, 2),
            "process_count": self.process_count,
            "memory_utilization": round(self.memory_utilization, 2),
            "interface_packet_rate": round(self.interface_packet_rate, 2),
            "bandwidth_utilization": round(self.bandwidth_utilization, 4),
            "throughput_mbps": round(self.throughput_mbps, 2),
            "latency_ms": round(self.latency_ms, 3),
            "jitter_ms": round(self.jitter_ms, 3),
            "packet_loss": round(self.packet_loss, 6),
            "queue_occupancy": self.queue_occupancy,
            "interface_errors": self.interface_errors,
            "bgp_events": self.bgp_events,
            "ospf_events": self.ospf_events,
            "tunnel_latency_ms": round(self.tunnel_latency_ms, 3),
            "tunnel_packet_loss": round(self.tunnel_packet_loss, 6),
            "tunnel_jitter_ms": round(self.tunnel_jitter_ms, 3),
            "route_changes": self.route_changes,
            "link_availability": self.link_availability,
            "link_status": self.link_status,
        }


@dataclass
class TelemetryFrame:
    """Collection of telemetry records backed by a pandas DataFrame.

    Attributes:
        records: List of TelemetryRecord instances.
    """

    records: List[TelemetryRecord] = field(default_factory=list)

    def add_record(self, record: TelemetryRecord) -> None:
        """Append a telemetry record.

        Args:
            record: The record to add.
        """
        self.records.append(record)

    def extend(self, records: List[TelemetryRecord]) -> None:
        """Extend with multiple records.

        Args:
            records: Records to add.
        """
        self.records.extend(records)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all records to a pandas DataFrame.

        Returns:
            DataFrame with one row per record.
        """
        if not self.records:
            return pd.DataFrame()
        return pd.DataFrame([r.to_dict() for r in self.records])

    def clear(self) -> None:
        """Remove all records."""
        self.records.clear()

    @property
    def size(self) -> int:
        """Number of records in the frame."""
        return len(self.records)
