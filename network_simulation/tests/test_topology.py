"""Tests for the topology module (devices, links, network_builder, routing, qos)."""

from __future__ import annotations

import networkx as nx
import pytest

from network_simulation.topology.devices import Device
from network_simulation.topology.links import Link, Tunnel
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.qos import QoSEngine, QoSProfile
from network_simulation.topology.routing import RoutingEngine
from network_simulation.utils.constants import LinkStatus


class TestDevice:
    def test_device_creation(self, sample_device: Device) -> None:
        assert sample_device.name == "test-device-1"
        assert sample_device.role == "branch"
        assert sample_device.cpu_utilization == 30.0
        assert sample_device.routing_table == {}
        assert sample_device.connected_links == []

    def test_to_dict(self, sample_device: Device) -> None:
        d = sample_device.to_dict()
        assert d["device_name"] == "test-device-1"
        assert d["cpu_utilization"] == 30.0

    def test_update_correlated_metrics(self, sample_device: Device) -> None:
        sample_device.interface_packet_rate = 500.0
        sample_device.cpu_utilization = 50.0
        sample_device.process_count = 80
        sample_device.update_correlated_metrics()
        assert sample_device.cpu_temperature > 45.0
        assert sample_device.interrupt_rate > 2000.0
        assert sample_device.memory_utilization > 35.0


class TestLink:
    def test_link_creation(self, sample_link: Link) -> None:
        assert sample_link.link_id == "test-device-1_to_test-device-2"
        assert sample_link.status == LinkStatus.UP

    def test_to_dict(self, sample_link: Link) -> None:
        d = sample_link.to_dict()
        assert d["link_id"] == "test-device-1_to_test-device-2"
        assert d["status"] == "UP"

    def test_tunnel_creation(self, sample_tunnel: Tunnel) -> None:
        assert sample_tunnel.name == "test-tunnel-1"
        assert sample_tunnel.status == LinkStatus.UP

    def test_tunnel_to_dict(self, sample_tunnel: Tunnel) -> None:
        d = sample_tunnel.to_dict()
        assert d["tunnel_name"] == "test-tunnel-1"


class TestNetworkBuilder:
    def test_empty_builder(self) -> None:
        builder = NetworkBuilder()
        assert builder.graph.number_of_nodes() == 0

    def test_small_topology(self, small_topology: NetworkBuilder) -> None:
        assert small_topology.graph.number_of_nodes() == 3
        assert small_topology.graph.number_of_edges() == 2
        assert len(small_topology.tunnels) == 1

    def test_get_device(self, small_topology: NetworkBuilder) -> None:
        device = small_topology.get_device("dc-1")
        assert device.role == "datacenter"

    def test_get_device_raises(self, small_topology: NetworkBuilder) -> None:
        with pytest.raises(KeyError):
            small_topology.get_device("nonexistent")

    def test_get_link(self, small_topology: NetworkBuilder) -> None:
        link = small_topology.get_link("dc-1", "hub-1")
        assert link.link_type == "mpls_core"

    def test_get_all_devices(self, small_topology: NetworkBuilder) -> None:
        devices = small_topology.get_all_devices()
        assert len(devices) == 3

    def test_get_all_links(self, small_topology: NetworkBuilder) -> None:
        links = small_topology.get_all_links()
        assert len(links) == 2

    def test_get_devices_by_role(self, small_topology: NetworkBuilder) -> None:
        branches = small_topology.get_devices_by_role("branch")
        assert len(branches) == 1

    def test_links_for_device(self, small_topology: NetworkBuilder) -> None:
        links = small_topology.links_for_device("hub-1")
        assert len(links) == 2

    def test_to_dict(self, small_topology: NetworkBuilder) -> None:
        d = small_topology.to_dict()
        assert len(d["devices"]) == 3
        assert len(d["links"]) == 2
        assert len(d["tunnels"]) == 1


class TestRoutingEngine:
    def test_recompute_all(self, small_topology: NetworkBuilder) -> None:
        engine = RoutingEngine(small_topology.graph)
        engine.recompute_all()
        device = small_topology.get_device("dc-1")
        assert len(device.routing_table) > 0

    def test_bgp_event(self, routing_engine: RoutingEngine) -> None:
        routing_engine.trigger_bgp_event()
        assert routing_engine.bgp_events == 1

    def test_ospf_event(self, routing_engine: RoutingEngine) -> None:
        routing_engine.trigger_ospf_event()
        assert routing_engine.ospf_events == 1

    def test_route_change_tracking(self, routing_engine: RoutingEngine) -> None:
        old = routing_engine.route_changes
        routing_engine.recompute_all()
        assert routing_engine.route_changes >= old

    def test_to_dict(self, routing_engine: RoutingEngine) -> None:
        d = routing_engine.to_dict()
        assert "bgp_events" in d


class TestQoSEngine:
    def test_register_and_get_profile(self) -> None:
        engine = QoSEngine()
        profile = QoSProfile(name="test", priority=3)
        engine.register_profile(profile)
        assert engine.get_profile("test") is profile

    def test_effective_bandwidth(self, sample_link: Link) -> None:
        engine = QoSEngine()
        engine.register_profile(QoSProfile(
            name="high", bandwidth_guarantee_fraction=0.5
        ))
        bw = engine.effective_bandwidth(sample_link, "high")
        assert bw == 500.0

    def test_latency_bound(self, sample_link: Link) -> None:
        engine = QoSEngine()
        engine.register_profile(QoSProfile(
            name="critical", latency_bound_ms=20.0
        ))
        assert engine.is_latency_within_bound(sample_link, "critical")

    def test_to_dict(self) -> None:
        engine = QoSEngine()
        engine.register_profile(QoSProfile(name="test"))
        d = engine.to_dict()
        assert "test" in d
