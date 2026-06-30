"""Traffic generator that simulates enterprise application traffic.

Updates device and link metrics each tick based on time-of-day traffic
profiles, creating a feedback loop where traffic demand drives CPU,
memory, link utilization, queue length, and latency.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from network_simulation.topology.devices import Device
from network_simulation.topology.links import Link
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.traffic.application_profiles import (
    ApplicationProfile,
    TrafficMix,
)
from network_simulation.traffic.bandwidth_model import BandwidthModel
from network_simulation.utils.constants import DeviceRole
from network_simulation.utils.helpers import (
    is_weekend,
    load_yaml_config,
    seconds_since_midnight,
)
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class TrafficGenerator:
    """Generates traffic and updates device/link state each tick.

    The single ``update`` method performs one complete traffic cycle:
    computes demand, applies it to devices and links, and produces a
    traceable mapping from traffic volume to metric changes.
    """

    def __init__(
        self,
        network_builder: NetworkBuilder,
        config_path: Path,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        """Initialise the traffic generator.

        Args:
            network_builder: Built network topology.
            config_path: Path to traffic.yaml.
            rng: NumPy random generator for burst sampling.
        """
        self._network = network_builder
        self._rng = rng if rng is not None else np.random.default_rng()
        config = load_yaml_config(config_path)
        self._traffic_mix = self._build_traffic_mix(config)
        self._bandwidth_model = BandwidthModel(self._traffic_mix, self._rng)
        self._device_weights = config.get("per_device_traffic_weights", {})
        self._office_hours = config.get("office_hours", {})

    def _build_traffic_mix(self, config: Dict[str, Any]) -> TrafficMix:
        """Build a TrafficMix from parsed YAML configuration.

        Args:
            config: Parsed traffic.yaml contents.

        Returns:
            Configured TrafficMix instance.
        """
        traffic_cfg = config.get("traffic", {})
        profiles = []
        for app_cfg in traffic_cfg.get("applications", []):
            profiles.append(
                ApplicationProfile(
                    name=app_cfg["name"],
                    description=app_cfg.get("description", ""),
                    base_bandwidth_mbps=app_cfg.get("base_bandwidth_mbps", 10.0),
                    burst_factor=app_cfg.get("burst_factor", 2.0),
                    burst_probability=app_cfg.get("burst_probability", 0.1),
                    priority=app_cfg.get("priority", "medium"),
                    time_of_day_profile=app_cfg.get("time_of_day_profile", []),
                    cpu_load_factor=app_cfg.get("cpu_load_factor", 0.1),
                    memory_load_factor=app_cfg.get("memory_load_factor", 0.08),
                    latency_sensitivity_ms=app_cfg.get(
                        "latency_sensitivity_ms", 100.0
                    ),
                )
            )
        office = traffic_cfg.get("office_hours", {})
        return TrafficMix(
            profiles=profiles,
            weekend_multiplier=office.get("weekend_multiplier", 0.3),
            office_hours_start=office.get("start_hour", 8),
            office_hours_end=office.get("end_hour", 18),
            peak_start=office.get("peak_start_hour", 10),
            peak_end=office.get("peak_end_hour", 15),
        )

    def update(self, current_time: datetime) -> None:
        """Run one traffic generation cycle at the given simulation time.

        This is the single causal function for traffic-driven metric
        changes. All device and link state updates happen here so that
        the mapping from traffic volume to telemetry is traceable.

        Args:
            current_time: Current simulation datetime (UTC).
        """
        hour = current_time.hour + current_time.minute / 60.0
        is_we = is_weekend(current_time)

        for device in self._network.get_all_devices():
            weight = self._device_weights.get(device.role, 1.0)
            demands = self._bandwidth_model.compute_total_demand(
                hour, is_we, weight
            )
            total_bandwidth = sum(demands.values())
            cpu_load = sum(
                d * (self._find_profile(name).cpu_load_factor)
                for name, d in demands.items()
            )
            mem_load = sum(
                d * (self._find_profile(name).memory_load_factor)
                for name, d in demands.items()
            )

            device.interface_packet_rate = total_bandwidth * 1000.0 / 8.0
            prev_cpu = device.cpu_utilization
            device.cpu_utilization = min(
                100.0,
                device.base_cpu + cpu_load * 2.0,
            )
            device.cpu_growth_rate = (
                device.cpu_utilization - prev_cpu
            )
            device.process_count = int(
                device.base_process_count + total_bandwidth * 0.05
            )
            device.update_correlated_metrics()

        for link in self._network.get_all_links():
            src_device = self._network.get_device(link.source)
            tgt_device = self._network.get_device(link.target)
            offered_load = (
                src_device.interface_packet_rate
                + tgt_device.interface_packet_rate
            ) / 2.0
            offered_mbps = offered_load * 8.0 / 1000.0
            link.utilization = min(
                1.0, offered_mbps / max(link.bandwidth_mbps, 0.001)
            )
            link.latency_ms = link.base_latency_ms * (
                1.0 + 2.0 * link.utilization
            )
            link.jitter_ms = link.base_jitter_ms * (
                1.0 + link.utilization
            )
            link.queue_length = int(
                link.utilization * 1024.0
            )
            link.packet_loss = link.base_packet_loss * (
                1.0 + 10.0 * link.utilization
            )

    def _find_profile(self, name: str) -> ApplicationProfile:
        """Find an application profile by name.

        Args:
            name: Profile name.

        Returns:
            Matching ApplicationProfile.
        """
        return self._traffic_mix.get_profile(name)

    @property
    def traffic_mix(self) -> TrafficMix:
        """Return the current traffic mix."""
        return self._traffic_mix
