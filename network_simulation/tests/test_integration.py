"""Integration tests that exercise the full simulation pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_simulation.fault_injection.bgp_flap import BgpFlapInjector
from network_simulation.fault_injection.congestion import CongestionInjector
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
from network_simulation.fault_injection.tunnel_failure import (
    TunnelFailureInjector,
)
from network_simulation.monte_carlo.simulator import MonteCarloSimulator


class TestMonteCarloSimulator:
    def test_simulator_runs_full_pipeline(self, tmp_path: Path) -> None:
        config_dir = Path(__file__).parent.parent / "config"
        if not config_dir.exists():
            pytest.skip("Config directory not found")
        output_dir = tmp_path / "output"
        simulator = MonteCarloSimulator(config_dir, output_dir)

        routing_engine = simulator._routing_engine
        network_builder = simulator._network_builder

        simulator.register_injector(
            "congestion", CongestionInjector(network_builder)
        )
        simulator.register_injector(
            "bgp_flap", BgpFlapInjector(network_builder, routing_engine)
        )
        simulator.register_injector(
            "ospf_failure",
            OspfFailureInjector(network_builder, routing_engine),
        )
        simulator.register_injector(
            "tunnel_failure", TunnelFailureInjector(network_builder)
        )
        simulator.register_injector(
            "mpls_failure", MplsFailureInjector(network_builder)
        )
        simulator.register_injector(
            "controller_error", ControllerErrorInjector(network_builder)
        )
        simulator.register_injector(
            "cpu_overload", CpuOverloadInjector(network_builder)
        )
        simulator.register_injector(
            "memory_exhaustion",
            MemoryExhaustionInjector(network_builder),
        )
        simulator.register_injector(
            "packet_loss_escalation",
            PacketLossEscalationInjector(network_builder),
        )

        summary = simulator.run()
        assert summary["total_ticks"] > 0
        assert summary["telemetry_records"] > 0

        output_files = list(output_dir.glob("*"))
        assert any(f.name == "telemetry.csv" for f in output_files)
        assert any(f.name == "telemetry.json" for f in output_files)
        assert any(f.name == "ground_truth.csv" for f in output_files)
        assert any(f.name == "fault_events.json" for f in output_files)
        assert any(f.name == "simulation_summary.json" for f in output_files)
        assert any(f.name == "metadata.json" for f in output_files)

    def test_simulator_with_zero_ticks(self, tmp_path: Path) -> None:
        config_dir = Path(__file__).parent.parent / "config"
        if not config_dir.exists():
            pytest.skip("Config directory not found")
        output_dir = tmp_path / "output"
        simulator = MonteCarloSimulator(config_dir, output_dir)
        simulator._total_ticks = 0
        summary = simulator.run()
        assert summary["total_ticks"] == 1
