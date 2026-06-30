"""Tests for all fault injectors and the recovery engine."""

from __future__ import annotations

import pytest

from network_simulation.fault_injection.congestion import CongestionInjector
from network_simulation.fault_injection.bgp_flap import BgpFlapInjector
from network_simulation.fault_injection.ospf_failure import OspfFailureInjector
from network_simulation.fault_injection.tunnel_failure import TunnelFailureInjector
from network_simulation.fault_injection.mpls_failure import MplsFailureInjector
from network_simulation.fault_injection.controller_error import (
    ControllerErrorInjector,
)
from network_simulation.fault_injection.cpu_overload import CpuOverloadInjector
from network_simulation.fault_injection.memory_exhaustion import (
    MemoryExhaustionInjector,
)
from network_simulation.fault_injection.packet_loss_escalation import (
    PacketLossEscalationInjector,
)
from network_simulation.fault_injection.recovery import RecoveryEngine
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine
from network_simulation.utils.constants import LinkStatus


class TestCongestionInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = CongestionInjector(small_topology)
        fault = ScheduledFault(
            event_id="c-1",
            fault_type="congestion",
            severity=0.5,
            affected_links=["dc-1_to_hub-1"],
            params={"bandwidth_reduction_range": 0.3, "latency_multiplier_range": 2.0},
        )
        link = small_topology.get_link("dc-1", "hub-1")
        original_bw = link.bandwidth_mbps
        injector.apply(fault)
        assert link.bandwidth_mbps < original_bw
        assert link.status == LinkStatus.DEGRADED
        injector.recover(fault)
        assert link.bandwidth_mbps == original_bw
        assert link.status == LinkStatus.UP

    def test_serialize(self, small_topology: NetworkBuilder) -> None:
        injector = CongestionInjector(small_topology)
        assert injector.serialize()["injector"] == "congestion"


class TestBgpFlapInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        routing = RoutingEngine(small_topology.graph)
        routing.recompute_all()
        injector = BgpFlapInjector(small_topology, routing)
        fault = ScheduledFault(
            event_id="bgp-1",
            fault_type="bgp_flap",
            affected_devices=["dc-1"],
            params={"prefix_withdrawal_rate": 0.5},
        )
        device = small_topology.get_device("dc-1")
        original_routes = len(device.routing_table)
        injector.apply(fault)
        assert routing.bgp_events > 0
        injector.recover(fault)

    def test_serialize(self, small_topology: NetworkBuilder) -> None:
        routing = RoutingEngine(small_topology.graph)
        injector = BgpFlapInjector(small_topology, routing)
        assert injector.serialize()["injector"] == "bgp_flap"


class TestOspfFailureInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        routing = RoutingEngine(small_topology.graph)
        injector = OspfFailureInjector(small_topology, routing)
        fault = ScheduledFault(
            event_id="ospf-1",
            fault_type="ospf_failure",
            affected_links=["dc-1_to_hub-1"],
            params={"adjacency_flap_probability": 1.0},
        )
        injector.apply(fault)
        assert routing.ospf_events > 0
        injector.recover(fault)

    def test_serialize(self, small_topology: NetworkBuilder) -> None:
        routing = RoutingEngine(small_topology.graph)
        injector = OspfFailureInjector(small_topology, routing)
        assert injector.serialize()["injector"] == "ospf_failure"


class TestTunnelFailureInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = TunnelFailureInjector(small_topology)
        fault = ScheduledFault(
            event_id="tun-1",
            fault_type="tunnel_failure",
            affected_devices=["hub-1"],
            params={
                "latency_increase_range": 3.0,
                "jitter_increase_range": 4.0,
            },
        )
        tunnel = small_topology.tunnels["ipsec-hub-to-branch1"]
        original_latency = tunnel.latency_ms
        injector.apply(fault)
        assert tunnel.latency_ms > original_latency
        assert tunnel.status == LinkStatus.DEGRADED
        injector.recover(fault)
        assert tunnel.latency_ms == original_latency
        assert tunnel.status == LinkStatus.UP


class TestMplsFailureInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = MplsFailureInjector(small_topology)
        fault = ScheduledFault(
            event_id="mpls-1",
            fault_type="mpls_failure",
            affected_devices=["dc-1"],
            params={
                "label_switching_delay_multiplier": 3.0,
                "lsp_degradation": 0.4,
            },
        )
        link = small_topology.get_link("dc-1", "hub-1")
        original_bw = link.bandwidth_mbps
        injector.apply(fault)
        assert link.bandwidth_mbps < original_bw
        assert link.status == LinkStatus.DEGRADED
        injector.recover(fault)
        assert link.bandwidth_mbps == original_bw
        assert link.status == LinkStatus.UP


class TestControllerErrorInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = ControllerErrorInjector(small_topology)
        device = small_topology.get_device("dc-1")
        device.cpu_utilization = 30.0
        device.memory_utilization = 40.0
        fault = ScheduledFault(
            event_id="ctrl-1",
            fault_type="controller_error",
            affected_devices=["dc-1"],
            params={"misconfiguration_impact": 0.3},
        )
        original_cpu = device.cpu_utilization
        original_mem = device.memory_utilization
        injector.apply(fault)
        assert device.cpu_utilization > original_cpu
        assert device.memory_utilization > original_mem
        injector.recover(fault)
        assert device.cpu_utilization == original_cpu
        assert device.memory_utilization == original_mem


class TestCpuOverloadInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = CpuOverloadInjector(small_topology)
        fault = ScheduledFault(
            event_id="cpu-1",
            fault_type="cpu_overload",
            affected_devices=["hub-1"],
            params={
                "cpu_increase_range": 40.0,
                "temp_increase_coefficient": 2.0,
                "process_spike_count": 50,
                "interrupt_spike_rate": 3000.0,
            },
        )
        device = small_topology.get_device("hub-1")
        original_cpu = device.cpu_utilization
        injector.apply(fault)
        assert device.cpu_utilization > original_cpu
        injector.recover(fault)
        assert device.cpu_utilization == original_cpu


class TestMemoryExhaustionInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = MemoryExhaustionInjector(small_topology)
        fault = ScheduledFault(
            event_id="mem-1",
            fault_type="memory_exhaustion",
            affected_devices=["branch-1"],
            params={
                "memory_increase_range": 30.0,
                "process_leak_count": 40,
            },
        )
        device = small_topology.get_device("branch-1")
        original_mem = device.memory_utilization
        injector.apply(fault)
        assert device.memory_utilization > original_mem
        injector.recover(fault)
        assert device.memory_utilization == original_mem


class TestPacketLossEscalationInjector:
    def test_apply_and_recover(
        self, small_topology: NetworkBuilder
    ) -> None:
        injector = PacketLossEscalationInjector(small_topology)
        fault = ScheduledFault(
            event_id="pl-1",
            fault_type="packet_loss_escalation",
            affected_links=["dc-1_to_hub-1"],
            params={
                "loss_base_increase": 0.02,
                "loss_escalation_rate": 0.005,
            },
        )
        link = small_topology.get_link("dc-1", "hub-1")
        original_loss = link.packet_loss
        injector.apply(fault)
        assert link.packet_loss > original_loss
        injector.recover(fault)
        assert link.packet_loss == original_loss


class TestRecoveryEngine:
    def test_recovery(self, small_topology: NetworkBuilder) -> None:
        engine = RecoveryEngine(small_topology)
        fault = ScheduledFault(
            event_id="r-1",
            fault_type="congestion",
            recovery_method="automatic",
        )
        engine.recover(fault)

    def test_hard_reset_device(self, small_topology: NetworkBuilder) -> None:
        engine = RecoveryEngine(small_topology)
        device = small_topology.get_device("dc-1")
        device.cpu_utilization = 95.0
        engine.hard_reset_device("dc-1")
        assert device.cpu_utilization == device.base_cpu

    def test_hard_reset_unknown(self, small_topology: NetworkBuilder) -> None:
        engine = RecoveryEngine(small_topology)
        engine.hard_reset_device("nonexistent")
