"""Basic tests for visualization modules (smoke tests that plots don't crash)."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.telemetry.metrics import TelemetryFrame, TelemetryRecord
from network_simulation.visualization.fault_timeline import FaultTimelinePlotter
from network_simulation.visualization.telemetry_dashboard import TelemetryDashboard
from network_simulation.visualization.topology_plot import TopologyPlotter


class TestTopologyPlotter:
    def test_plot_saves(self, small_topology: NetworkBuilder, tmp_path: Path) -> None:
        plotter = TopologyPlotter(small_topology)
        out = tmp_path / "topology.png"
        plotter.plot(output_path=out)
        assert out.exists()


class TestTelemetryDashboard:
    def test_plot_empty(self, tmp_path: Path) -> None:
        frame = TelemetryFrame()
        dashboard = TelemetryDashboard(frame)
        out = tmp_path / "dashboard.png"
        dashboard.plot(output_path=out)


class TestFaultTimelinePlotter:
    def test_plot_empty(self, tmp_path: Path) -> None:
        plotter = FaultTimelinePlotter([])
        out = tmp_path / "timeline.png"
        plotter.plot(output_path=out)

    def test_plot_with_events(self, tmp_path: Path) -> None:
        events = [
            {
                "event_id": "e1",
                "fault_type": "congestion",
                "severity": 0.7,
                "tick": 10,
                "duration_ticks": 20,
            },
        ]
        plotter = FaultTimelinePlotter(events)
        out = tmp_path / "timeline.png"
        plotter.plot(output_path=out)
        assert out.exists()
