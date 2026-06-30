"""Tests for the labeling module (ground_truth, event_logger, dataset_builder)."""

from __future__ import annotations

import pytest

from network_simulation.labeling.dataset_builder import DatasetBuilder
from network_simulation.labeling.event_logger import EventLogger
from network_simulation.labeling.ground_truth import GroundTruthLabel
from network_simulation.monte_carlo.scheduler import ScheduledFault
from network_simulation.telemetry.metrics import TelemetryFrame, TelemetryRecord


class TestGroundTruthLabel:
    def test_label_creation(self) -> None:
        label = GroundTruthLabel(
            event_id="evt-1",
            fault_type="congestion",
            device="hub-1",
            severity=0.7,
            start_time="2025-01-01T12:00:00Z",
            end_time="2025-01-01T12:10:00Z",
            recovery_time="2025-01-01T12:10:00Z",
            affected_services=["erp", "web"],
            affected_links=["link-1"],
            expected_impact="Increased latency",
        )
        assert label.event_id == "evt-1"
        assert label.fault_type == "congestion"

    def test_to_dict(self) -> None:
        label = GroundTruthLabel(
            event_id="evt-1",
            fault_type="bgp_flap",
            device="dc-1",
            severity=0.5,
        )
        d = label.to_dict()
        assert d["event_id"] == "evt-1"
        assert d["severity"] == 0.5


class TestEventLogger:
    def test_log_start_end(self) -> None:
        logger = EventLogger()
        fault = ScheduledFault(
            event_id="evt-1",
            fault_type="congestion",
            severity=0.6,
            affected_devices=["hub-1"],
            affected_links=["link-1"],
        )
        logger.log_fault_start(fault, "2025-01-01T12:00:00Z")
        assert fault.event_id in logger.get_active_events()
        logger.log_fault_end(fault, "2025-01-01T12:10:00Z")
        assert fault.event_id not in logger.get_active_events()
        labels = logger.get_labels()
        assert len(labels) == 1
        assert labels[0].fault_type == "congestion"

    def test_no_events(self) -> None:
        logger = EventLogger()
        assert logger.get_labels() == []
        assert logger.get_active_events() == {}


class TestDatasetBuilder:
    def test_empty_builder(self) -> None:
        builder = DatasetBuilder()
        df = builder.build_merged_dataset()
        assert df.empty

    def test_ingest_telemetry(self) -> None:
        builder = DatasetBuilder()
        frame = TelemetryFrame()
        frame.add_record(TelemetryRecord(
            tick=0, timestamp="t", device_name="d", record_type="device",
        ))
        builder.ingest_telemetry(frame)
        summary = builder.dataset_summary()
        assert summary["telemetry_rows"] == 1

    def test_ingest_labels(self) -> None:
        builder = DatasetBuilder()
        builder.ingest_labels([
            GroundTruthLabel(event_id="e1", fault_type="congestion"),
        ])
        summary = builder.dataset_summary()
        assert summary["label_count"] == 1

    def test_dataset_summary_empty(self) -> None:
        builder = DatasetBuilder()
        summary = builder.dataset_summary()
        assert summary["telemetry_rows"] == 0
        assert summary["label_count"] == 0
