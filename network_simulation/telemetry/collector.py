"""Telemetry collector that reads the full topology state each tick.

Produces TelemetryRecord instances for every device, link, and tunnel.
"""

from __future__ import annotations

from typing import List, Optional

from network_simulation.telemetry.metrics import TelemetryRecord
from network_simulation.telemetry.timestamp import SimulationTimestamp
from network_simulation.topology.links import Link, Tunnel
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class TelemetryCollector:
    """Collects telemetry from the topology and routing engine each tick.

    This is the single point where raw topology state is converted into
    structured TelemetryRecord objects.
    """

    def __init__(
        self,
        network_builder: NetworkBuilder,
        routing_engine: RoutingEngine,
    ) -> None:
        """Initialise the collector.

        Args:
            network_builder: The network topology.
            routing_engine: The routing engine (provides BGP/OSPF counts).
        """
        self._network = network_builder
        self._routing = routing_engine

    def collect(
        self, timestamp: SimulationTimestamp
    ) -> List[TelemetryRecord]:
        """Collect telemetry from all devices, links, and tunnels.

        Args:
            timestamp: Current simulation timestamp.

        Returns:
            List of TelemetryRecord instances for this tick.
        """
        records: List[TelemetryRecord] = []
        self._collect_device_records(timestamp, records)
        self._collect_link_records(timestamp, records)
        self._collect_tunnel_records(timestamp, records)
        return records

    def _collect_device_records(
        self,
        timestamp: SimulationTimestamp,
        records: List[TelemetryRecord],
    ) -> None:
        """Append device telemetry records.

        Args:
            timestamp: Current simulation timestamp.
            records: Output list to append to.
        """
        for device in self._network.get_all_devices():
            record = TelemetryRecord(
                tick=timestamp.tick,
                timestamp=timestamp.iso_format,
                device_name=device.name,
                record_type="device",
                cpu_utilization=device.cpu_utilization,
                cpu_growth_rate=device.cpu_growth_rate,
                cpu_temperature=device.cpu_temperature,
                interrupt_rate=device.interrupt_rate,
                process_count=device.process_count,
                memory_utilization=device.memory_utilization,
                interface_packet_rate=device.interface_packet_rate,
                bgp_events=self._routing.bgp_events,
                ospf_events=self._routing.ospf_events,
                route_changes=self._routing.route_changes,
            )
            records.append(record)

    def _collect_link_records(
        self,
        timestamp: SimulationTimestamp,
        records: List[TelemetryRecord],
    ) -> None:
        """Append link telemetry records.

        Args:
            timestamp: Current simulation timestamp.
            records: Output list to append to.
        """
        for link in self._network.get_all_links():
            record = TelemetryRecord(
                tick=timestamp.tick,
                timestamp=timestamp.iso_format,
                device_name=link.link_id,
                record_type="link",
                bandwidth_utilization=link.utilization,
                throughput_mbps=link.utilization * link.bandwidth_mbps,
                latency_ms=link.latency_ms,
                jitter_ms=link.jitter_ms,
                packet_loss=link.packet_loss,
                queue_occupancy=link.queue_length,
                interface_errors=link.interface_errors,
                link_availability=(
                    1.0 if link.status == LinkStatus.UP else
                    0.5 if link.status == LinkStatus.DEGRADED else 0.0
                ),
                link_status=link.status,
            )
            records.append(record)

    def _collect_tunnel_records(
        self,
        timestamp: SimulationTimestamp,
        records: List[TelemetryRecord],
    ) -> None:
        """Append tunnel telemetry records.

        Args:
            timestamp: Current simulation timestamp.
            records: Output list to append to.
        """
        for tunnel in self._network.tunnels.values():
            record = TelemetryRecord(
                tick=timestamp.tick,
                timestamp=timestamp.iso_format,
                device_name=tunnel.name,
                record_type="tunnel",
                latency_ms=tunnel.latency_ms,
                jitter_ms=tunnel.jitter_ms,
                packet_loss=tunnel.packet_loss,
                throughput_mbps=tunnel.throughput_mbps,
                tunnel_latency_ms=tunnel.latency_ms,
                tunnel_packet_loss=tunnel.packet_loss,
                tunnel_jitter_ms=tunnel.jitter_ms,
                bandwidth_utilization=tunnel.utilization,
                link_availability=(
                    1.0 if tunnel.status == LinkStatus.UP else
                    0.5 if tunnel.status == LinkStatus.DEGRADED else 0.0
                ),
                link_status=tunnel.status,
            )
            records.append(record)
