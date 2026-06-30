"""Shared test fixtures for the network simulation test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator

import networkx as nx
import numpy as np
import pytest

from network_simulation.fault_injection.congestion import CongestionInjector
from network_simulation.fault_injection.bgp_flap import BgpFlapInjector
from network_simulation.fault_injection.controller_error import (
    ControllerErrorInjector,
)
from network_simulation.fault_injection.cpu_overload import CpuOverloadInjector
from network_simulation.fault_injection.memory_exhaustion import (
    MemoryExhaustionInjector,
)
from network_simulation.fault_injection.mpls_failure import MplsFailureInjector
from network_simulation.fault_injection.ospf_failure import OspfFailureInjector
from network_simulation.fault_injection.packet_loss_escalation import (
    PacketLossEscalationInjector,
)
from network_simulation.fault_injection.recovery import RecoveryEngine
from network_simulation.fault_injection.tunnel_failure import (
    TunnelFailureInjector,
)
from network_simulation.monte_carlo.distributions import DistributionSampler
from network_simulation.monte_carlo.random_seed import RandomSeedManager
from network_simulation.monte_carlo.scheduler import (
    FaultScheduler,
    ScheduledFault,
)
from network_simulation.telemetry.collector import TelemetryCollector
from network_simulation.telemetry.metrics import TelemetryFrame, TelemetryRecord
from network_simulation.telemetry.timestamp import SimulationTimestamp
from network_simulation.topology.devices import Device
from network_simulation.topology.links import Link, Tunnel
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.qos import QoSEngine, QoSProfile
from network_simulation.topology.routing import RoutingEngine
from network_simulation.traffic.application_profiles import (
    ApplicationProfile,
    TrafficMix,
)
from network_simulation.traffic.bandwidth_model import BandwidthModel
from network_simulation.traffic.traffic_generator import TrafficGenerator
from network_simulation.utils.constants import LinkStatus


@pytest.fixture
def fixed_seed() -> int:
    """Return a fixed seed for reproducible tests."""
    return 42


@pytest.fixture
def rng() -> np.random.Generator:
    """Return a seeded random generator for tests."""
    return np.random.default_rng(42)


@pytest.fixture
def sample_device() -> Device:
    """Return a basic Device with default values."""
    return Device(
        name="test-device-1",
        role="branch",
        device_type="isr_4451",
        location="test-location",
        os="ios_xe",
        software_version="17.3.3",
        cpu_utilization=30.0,
        interrupt_rate=2000.0,
        process_count=55,
        memory_utilization=35.0,
        interface_packet_rate=100.0,
        base_cpu=25.0,
        base_memory=35.0,
        base_process_count=55,
        base_interrupt_rate=2000.0,
        cpu_temp_alpha=2.0,
        memory_gamma_process=0.10,
        memory_gamma_cpu=0.06,
        interrupt_beta=0.005,
    )


@pytest.fixture
def sample_link() -> Link:
    """Return a basic Link with default values."""
    return Link(
        link_id="test-device-1_to_test-device-2",
        source="test-device-1",
        target="test-device-2",
        link_type="mpls_access",
        status=LinkStatus.UP,
        bandwidth_mbps=1000.0,
        latency_ms=10.0,
        base_latency_ms=10.0,
        jitter_ms=0.5,
        base_jitter_ms=0.5,
        packet_loss=0.001,
        base_packet_loss=0.001,
        mtu=1500,
    )


@pytest.fixture
def sample_tunnel() -> Tunnel:
    """Return a basic Tunnel with default values."""
    return Tunnel(
        name="test-tunnel-1",
        source="test-device-1",
        target="test-device-2",
        tunnel_type="ipsec",
        status=LinkStatus.UP,
        latency_ms=15.0,
        base_latency_ms=15.0,
        jitter_ms=1.0,
        base_jitter_ms=1.0,
        packet_loss=0.001,
        base_packet_loss=0.001,
        throughput_mbps=100.0,
        utilization=0.1,
    )


@pytest.fixture
def small_topology() -> Generator[NetworkBuilder, None, None]:
    """Build a small synthetic topology for fast tests."""
    builder = NetworkBuilder()
    devices = [
        Device(name="dc-1", role="datacenter"),
        Device(name="hub-1", role="mpls_hub"),
        Device(name="branch-1", role="branch"),
    ]
    for d in devices:
        builder.graph.add_node(d.name, device=d)

    links = [
        Link(
            link_id="dc-1_to_hub-1",
            source="dc-1", target="hub-1",
            link_type="mpls_core",
            bandwidth_mbps=10000.0,
        ),
        Link(
            link_id="hub-1_to_branch-1",
            source="hub-1", target="branch-1",
            link_type="mpls_access",
            bandwidth_mbps=1000.0,
        ),
    ]
    for l in links:
        builder.graph.add_edge(l.source, l.target, link=l)
        builder._register_link_on_devices(l)

    tunnel = Tunnel(
        name="ipsec-hub-to-branch1",
        source="hub-1",
        target="branch-1",
    )
    builder.tunnels[tunnel.name] = tunnel
    return builder


@pytest.fixture
def routing_engine(
    small_topology: NetworkBuilder,
) -> RoutingEngine:
    """Return a RoutingEngine for the small topology."""
    engine = RoutingEngine(small_topology.graph)
    engine.recompute_all()
    return engine


@pytest.fixture
def fault_config() -> Dict[str, Any]:
    """Return a minimal faults.yaml config for testing."""
    return {
        "monte_carlo": {
            "fault_probability_per_tick": 0.1,
            "max_concurrent_faults": 2,
            "min_ticks_between_faults": 5,
            "fault_type_weights": {
                "congestion": 0.5,
                "bgp_flap": 0.5,
            },
        },
        "distributions": {
            "severity": {
                "type": "uniform",
                "scale_min": 0.3,
                "scale_max": 1.0,
            },
            "duration_ticks": {
                "type": "uniform",
                "min": 5,
                "max": 20,
            },
            "device_selection": {
                "type": "uniform",
                "count_min": 1,
                "count_max": 2,
            },
        },
        "fault_types": {
            "congestion": {
                "enabled": True,
                "recovery_methods": ["automatic"],
                "bandwidth_reduction_range": [0.2, 0.5],
                "latency_multiplier_range": [1.5, 3.0],
            },
            "bgp_flap": {
                "enabled": True,
                "recovery_methods": ["automatic"],
                "prefix_withdrawal_rate": [0.1, 0.3],
            },
        },
    }


@pytest.fixture
def sample_scheduled_fault() -> ScheduledFault:
    """Return a basic ScheduledFault for testing."""
    return ScheduledFault(
        event_id="test-event-001",
        fault_type="congestion",
        severity=0.7,
        duration_ticks=10,
        remaining_ticks=10,
        affected_devices=["test-device-1"],
        affected_links=["test-link-1"],
        recovery_method="automatic",
        params={"bandwidth_reduction_range": 0.5, "latency_multiplier_range": 2.0},
    )


@pytest.fixture
def seed_manager(fixed_seed: int) -> RandomSeedManager:
    """Return a RandomSeedManager for testing."""
    return RandomSeedManager(fixed_seed)


@pytest.fixture
def sampler(seed_manager: RandomSeedManager) -> DistributionSampler:
    """Return a DistributionSampler for testing."""
    return DistributionSampler(seed_manager.rng)


@pytest.fixture
def telemetry_collector(
    small_topology: NetworkBuilder,
    routing_engine: RoutingEngine,
) -> TelemetryCollector:
    """Return a TelemetryCollector for testing."""
    return TelemetryCollector(small_topology, routing_engine)


@pytest.fixture
def timestamp() -> SimulationTimestamp:
    """Return a SimulationTimestamp for tick 0."""
    return SimulationTimestamp.from_tick(0)
