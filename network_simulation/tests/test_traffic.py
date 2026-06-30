"""Tests for the traffic module (application profiles, bandwidth model, generator)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from network_simulation.traffic.application_profiles import (
    ApplicationProfile,
    TrafficMix,
)
from network_simulation.traffic.bandwidth_model import BandwidthModel
from network_simulation.traffic.traffic_generator import TrafficGenerator
from network_simulation.topology.network_builder import NetworkBuilder


class TestApplicationProfiles:
    def test_application_profile_creation(self) -> None:
        profile = ApplicationProfile(
            name="erp",
            base_bandwidth_mbps=50.0,
            burst_factor=2.5,
            priority="high",
        )
        assert profile.name == "erp"
        assert profile.base_bandwidth_mbps == 50.0

    def test_application_profile_to_dict(self) -> None:
        profile = ApplicationProfile(name="test")
        d = profile.to_dict()
        assert d["name"] == "test"

    def test_traffic_mix(self) -> None:
        p1 = ApplicationProfile(name="erp")
        p2 = ApplicationProfile(name="web")
        mix = TrafficMix(profiles=[p1, p2])
        assert mix.get_profile("erp") is p1
        with pytest.raises(KeyError):
            mix.get_profile("nonexistent")

    def test_traffic_mix_to_dict(self) -> None:
        mix = TrafficMix(profiles=[ApplicationProfile(name="test")])
        d = mix.to_dict()
        assert len(d["profiles"]) == 1


class TestBandwidthModel:
    def test_compute_demand(self, rng: np.random.Generator) -> None:
        profile = ApplicationProfile(
            name="test",
            base_bandwidth_mbps=100.0,
            burst_probability=0.0,
            time_of_day_profile=[
                {"hour": 0, "multiplier": 0.5},
                {"hour": 12, "multiplier": 1.0},
            ],
        )
        mix = TrafficMix(profiles=[profile])
        model = BandwidthModel(mix, rng)
        demand = model.compute_demand(profile, 12.0, False)
        assert demand == 100.0

    def test_weekend_multiplier(self, rng: np.random.Generator) -> None:
        profile = ApplicationProfile(
            name="test",
            base_bandwidth_mbps=100.0,
            burst_probability=0.0,
            time_of_day_profile=[
                {"hour": 12, "multiplier": 1.0},
            ],
        )
        mix = TrafficMix(profiles=[profile], weekend_multiplier=0.5)
        model = BandwidthModel(mix, rng)
        demand = model.compute_demand(profile, 12.0, True)
        assert demand == 50.0

    def test_burst(self, rng: np.random.Generator) -> None:
        profile = ApplicationProfile(
            name="test",
            base_bandwidth_mbps=100.0,
            burst_factor=3.0,
            burst_probability=1.0,
            time_of_day_profile=[{"hour": 12, "multiplier": 1.0}],
        )
        mix = TrafficMix(profiles=[profile])
        model = BandwidthModel(mix, rng)
        demand = model.compute_demand(profile, 12.0, False)
        assert demand == 300.0

    def test_peak_hour(self, rng: np.random.Generator) -> None:
        mix = TrafficMix(peak_start=10, peak_end=15)
        model = BandwidthModel(mix, rng)
        assert model.is_peak_hour(12.0)
        assert not model.is_peak_hour(8.0)


class TestTrafficGenerator:
    def test_update_devices(self, small_topology: NetworkBuilder) -> None:
        config_path = (
            Path(__file__).parent.parent / "config" / "traffic.yaml"
        )
        if not config_path.exists():
            pytest.skip("traffic.yaml not found")
        generator = TrafficGenerator(small_topology, config_path)
        from datetime import datetime, timezone
        dt = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
        generator.update(dt)
        for device in small_topology.get_all_devices():
            assert device.cpu_utilization > 0
            assert device.memory_utilization > 0
            assert len(device.routing_table) >= 0
