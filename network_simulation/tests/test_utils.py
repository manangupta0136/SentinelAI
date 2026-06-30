"""Tests for utils module (constants, helpers, logger)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from network_simulation.utils.constants import (
    SimulationConstants,
    LinkStatus,
    DeviceRole,
    FaultType,
)
from network_simulation.utils.helpers import (
    load_yaml_config,
    interpolate_time_of_day,
    truncate_normal,
    clamp,
    generate_event_id,
    is_weekend,
    seconds_since_midnight,
)
from network_simulation.utils.logger import setup_logging, get_logger


class TestConstants:
    def test_simulation_constants(self) -> None:
        c = SimulationConstants()
        assert c.SECONDS_PER_HOUR == 3600
        assert c.BITS_PER_BYTE == 8

    def test_link_status(self) -> None:
        assert LinkStatus.UP == "UP"
        assert LinkStatus.DOWN == "DOWN"

    def test_device_role(self) -> None:
        assert DeviceRole.DATACENTER == "datacenter"

    def test_fault_type(self) -> None:
        assert FaultType.CONGESTION == "congestion"


class TestHelpers:
    def test_interpolate_time_of_day_empty(self) -> None:
        assert interpolate_time_of_day(12.0, []) == 1.0

    def test_interpolate_time_of_day(self) -> None:
        profile = [
            {"hour": 0, "multiplier": 0.0},
            {"hour": 12, "multiplier": 1.0},
            {"hour": 24, "multiplier": 0.0},
        ]
        val = interpolate_time_of_day(12.0, profile)
        assert val == 1.0

    def test_clamp(self) -> None:
        assert clamp(5.0, 0.0, 10.0) == 5.0
        assert clamp(-1.0, 0.0, 10.0) == 0.0
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_generate_event_id(self) -> None:
        eid = generate_event_id()
        assert len(eid) == 16
        assert isinstance(eid, str)

    def test_is_weekend(self) -> None:
        from datetime import datetime, timezone
        saturday = datetime(2025, 1, 4, tzinfo=timezone.utc)
        monday = datetime(2025, 1, 6, tzinfo=timezone.utc)
        assert is_weekend(saturday) is True
        assert is_weekend(monday) is False

    def test_seconds_since_midnight(self) -> None:
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc)
        secs = seconds_since_midnight(dt)
        assert secs == 12 * 3600 + 30 * 60

    def test_load_yaml_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_yaml_config(Path("/nonexistent/file.yaml"))

    def test_truncate_normal(self) -> None:
        val = truncate_normal(0.5, 0.1, 0.0, 1.0)
        assert 0.0 <= val <= 1.0


class TestLogger:
    def test_setup_logging(self) -> None:
        setup_logging(level="DEBUG")
        logger = get_logger("test_logger")
        assert logger.isEnabledFor(logging.DEBUG)

    def test_get_logger(self) -> None:
        logger = get_logger("test")
        assert logger.name == "test"
