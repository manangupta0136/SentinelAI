"""Tests for the telemetry module (metrics, collector, exporters, timestamp)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Generator

import pandas as pd
import pytest

from network_simulation.telemetry.collector import TelemetryCollector
from network_simulation.telemetry.exporters import TelemetryExporter
from network_simulation.telemetry.metrics import TelemetryFrame, TelemetryRecord
from network_simulation.telemetry.timestamp import SimulationTimestamp
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine


class TestSimulationTimestamp:
    def test_from_tick_default(self) -> None:
        ts = SimulationTimestamp.from_tick(0)
        assert ts.tick == 0
        assert "1970" in ts.iso_format

    def test_iso_format(self) -> None:
        ts = SimulationTimestamp.from_tick(10, tick_interval_seconds=60)
        assert ts.iso_format.endswith("Z")
        assert "00:10:00" in ts.iso_format

    def test_to_dict(self) -> None:
        ts = SimulationTimestamp.from_tick(5)
        d = ts.to_dict()
        assert d["tick"] == 5


class TestTelemetryRecord:
    def test_record_creation(self) -> None:
        record = TelemetryRecord(
            tick=0,
            timestamp="2025-01-01T00:00:00Z",
            device_name="test-device",
            record_type="device",
            cpu_utilization=45.0,
        )
        assert record.cpu_utilization == 45.0

    def test_to_dict(self) -> None:
        record = TelemetryRecord(
            tick=1, timestamp="2025-01-01T00:01:00Z",
            device_name="d1", record_type="device",
        )
        d = record.to_dict()
        assert d["tick"] == 1
        assert d["device_name"] == "d1"


class TestTelemetryFrame:
    def test_empty_frame(self) -> None:
        frame = TelemetryFrame()
        assert frame.size == 0
        df = frame.to_dataframe()
        assert df.empty

    def test_add_record(self) -> None:
        frame = TelemetryFrame()
        record = TelemetryRecord(tick=0, timestamp="t", device_name="d", record_type="device")
        frame.add_record(record)
        assert frame.size == 1

    def test_to_dataframe(self) -> None:
        frame = TelemetryFrame()
        frame.add_record(TelemetryRecord(
            tick=0, timestamp="t", device_name="d", record_type="device",
            cpu_utilization=50.0,
        ))
        df = frame.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_clear(self) -> None:
        frame = TelemetryFrame()
        frame.add_record(TelemetryRecord(tick=0, timestamp="t", device_name="d", record_type="device"))
        frame.clear()
        assert frame.size == 0


class TestTelemetryCollector:
    def test_collect_devices(
        self,
        telemetry_collector: TelemetryCollector,
        timestamp: SimulationTimestamp,
    ) -> None:
        records = telemetry_collector.collect(timestamp)
        device_records = [r for r in records if r.record_type == "device"]
        assert len(device_records) == 3

    def test_collect_links(
        self,
        telemetry_collector: TelemetryCollector,
        timestamp: SimulationTimestamp,
    ) -> None:
        records = telemetry_collector.collect(timestamp)
        link_records = [r for r in records if r.record_type == "link"]
        assert len(link_records) == 2

    def test_collect_tunnels(
        self,
        telemetry_collector: TelemetryCollector,
        timestamp: SimulationTimestamp,
    ) -> None:
        records = telemetry_collector.collect(timestamp)
        tunnel_records = [r for r in records if r.record_type == "tunnel"]
        assert len(tunnel_records) == 1


class TestTelemetryExporter:
    @pytest.fixture
    def tmp_output(self, tmp_path: Path) -> Path:
        output = tmp_path / "output"
        output.mkdir()
        return output

    def test_export_telemetry_csv(
        self, tmp_output: Path
    ) -> None:
        exporter = TelemetryExporter(tmp_output)
        frame = TelemetryFrame()
        frame.add_record(TelemetryRecord(
            tick=0, timestamp="t", device_name="d", record_type="device",
        ))
        path = exporter.export_telemetry_csv(frame)
        assert path.exists()
        assert path.suffix == ".csv"

    def test_export_telemetry_json(
        self, tmp_output: Path
    ) -> None:
        exporter = TelemetryExporter(tmp_output)
        frame = TelemetryFrame()
        frame.add_record(TelemetryRecord(
            tick=0, timestamp="t", device_name="d", record_type="device",
        ))
        path = exporter.export_telemetry_json(frame)
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_export_ground_truth_csv(
        self, tmp_output: Path
    ) -> None:
        exporter = TelemetryExporter(tmp_output)
        path = exporter.export_ground_truth_csv([
            {"event_id": "e1", "fault_type": "congestion"},
        ])
        assert path.exists()

    def test_export_fault_events_json(
        self, tmp_output: Path
    ) -> None:
        exporter = TelemetryExporter(tmp_output)
        path = exporter.export_fault_events_json([
            {"event_id": "e1", "fault_type": "congestion"},
        ])
        assert path.exists()

    def test_export_summary_and_metadata(
        self, tmp_output: Path
    ) -> None:
        exporter = TelemetryExporter(tmp_output)
        path1 = exporter.export_simulation_summary({"ticks": 100})
        path2 = exporter.export_metadata({"seed": 42})
        assert path1.exists()
        assert path2.exists()
