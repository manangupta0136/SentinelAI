"""Tests for the monte_carlo module (random_seed, distributions, scheduler)."""

from __future__ import annotations

import numpy as np
import pytest

from network_simulation.monte_carlo.distributions import DistributionSampler
from network_simulation.monte_carlo.random_seed import RandomSeedManager
from network_simulation.monte_carlo.scheduler import (
    FaultScheduler,
    ScheduledFault,
)


class TestRandomSeedManager:
    def test_initial_seed(self) -> None:
        mgr = RandomSeedManager(42)
        assert mgr.seed == 42

    def test_reproducibility(self) -> None:
        mgr1 = RandomSeedManager(123)
        mgr2 = RandomSeedManager(123)
        assert mgr1.rng.uniform() == mgr2.rng.uniform()

    def test_reseed(self) -> None:
        mgr = RandomSeedManager(42)
        mgr.reseed(99)
        assert mgr.seed == 99

    def test_spawn(self) -> None:
        mgr = RandomSeedManager(42)
        child = mgr.spawn()
        assert isinstance(child, np.random.Generator)


class TestDistributionSampler:
    def test_sample_uniform(self, sampler: DistributionSampler) -> None:
        config = {"type": "uniform"}
        val = sampler.sample(config)
        assert 0.0 <= val <= 1.0

    def test_sample_beta(self, sampler: DistributionSampler) -> None:
        config = {
            "type": "beta",
            "params": {"alpha": 2.0, "beta": 5.0},
        }
        val = sampler.sample(config)
        assert 0.0 <= val <= 1.0

    def test_sample_with_scale(self, sampler: DistributionSampler) -> None:
        config = {
            "type": "uniform",
            "scale_min": 10.0,
            "scale_max": 20.0,
        }
        val = sampler.sample(config)
        assert 10.0 <= val <= 20.0

    def test_sample_with_clamp(self, sampler: DistributionSampler) -> None:
        config = {
            "type": "normal",
            "params": {"mean": 50.0, "std": 100.0},
            "min": 0.0,
            "max": 100.0,
        }
        val = sampler.sample(config)
        assert 0.0 <= val <= 100.0

    def test_sample_int(self, sampler: DistributionSampler) -> None:
        config = {"type": "uniform", "min": 5, "max": 10}
        val = sampler.sample_int(config)
        assert 5 <= val <= 10

    def test_sample_choice(self, sampler: DistributionSampler) -> None:
        choice = sampler.sample_choice(["a", "b", "c"])
        assert choice in ("a", "b", "c")

    def test_sample_choice_weighted(self, sampler: DistributionSampler) -> None:
        choice = sampler.sample_choice(["x", "y"], weights=[0.0, 1.0])
        assert choice == "y"

    def test_sample_bool(self, sampler: DistributionSampler) -> None:
        assert sampler.sample_bool(1.0) is True
        assert sampler.sample_bool(0.0) is False

    def test_unsupported_distribution(self, sampler: DistributionSampler) -> None:
        with pytest.raises(ValueError, match="Unsupported distribution"):
            sampler.sample({"type": "unknown"})


class TestFaultScheduler:
    def test_no_fault_at_prob_zero(
        self,
        small_topology,
        fault_config,
        sampler,
        seed_manager,
    ) -> None:
        cfg = fault_config.copy()
        cfg["monte_carlo"]["fault_probability_per_tick"] = 0.0
        scheduler = FaultScheduler(
            cfg, small_topology.graph, sampler, seed_manager
        )
        fault = scheduler.tick(0)
        assert fault is None

    def test_fault_at_prob_one(
        self,
        small_topology,
        fault_config,
        sampler,
        seed_manager,
    ) -> None:
        cfg = fault_config.copy()
        cfg["monte_carlo"]["fault_probability_per_tick"] = 1.0
        cfg["monte_carlo"]["min_ticks_between_faults"] = 0
        scheduler = FaultScheduler(
            cfg, small_topology.graph, sampler, seed_manager
        )
        fault = scheduler.tick(1)
        assert fault is not None
        assert fault.fault_type in ("congestion", "bgp_flap")
        assert fault.severity > 0
        assert fault.duration_ticks > 0

    def test_max_concurrent_faults(
        self,
        small_topology,
        fault_config,
        sampler,
        seed_manager,
    ) -> None:
        cfg = fault_config.copy()
        cfg["monte_carlo"]["fault_probability_per_tick"] = 1.0
        cfg["monte_carlo"]["max_concurrent_faults"] = 1
        cfg["monte_carlo"]["min_ticks_between_faults"] = 0
        scheduler = FaultScheduler(
            cfg, small_topology.graph, sampler, seed_manager
        )
        fault1 = scheduler.tick(1)
        assert fault1 is not None
        fault2 = scheduler.tick(2)
        assert fault2 is None

    def test_min_ticks_between(
        self,
        small_topology,
        fault_config,
        sampler,
        seed_manager,
    ) -> None:
        cfg = fault_config.copy()
        cfg["monte_carlo"]["fault_probability_per_tick"] = 1.0
        cfg["monte_carlo"]["min_ticks_between_faults"] = 10
        scheduler = FaultScheduler(
            cfg, small_topology.graph, sampler, seed_manager
        )
        f1 = scheduler.tick(1)
        assert f1 is not None
        f2 = scheduler.tick(2)
        assert f2 is None

    def test_active_faults_decrement(
        self,
        small_topology,
        fault_config,
        sampler,
        seed_manager,
    ) -> None:
        cfg = fault_config.copy()
        cfg["monte_carlo"]["fault_probability_per_tick"] = 1.0
        cfg["monte_carlo"]["max_concurrent_faults"] = 1
        cfg["monte_carlo"]["min_ticks_between_faults"] = 0
        scheduler = FaultScheduler(
            cfg, small_topology.graph, sampler, seed_manager
        )
        scheduler.tick(0)
        scheduler.tick(1)
        for f in scheduler.active_faults:
            assert f.remaining_ticks < f.duration_ticks


class TestScheduledFault:
    def test_default_creation(self) -> None:
        f = ScheduledFault()
        assert f.event_id == ""
        assert f.severity == 0.5

    def test_custom_creation(self) -> None:
        f = ScheduledFault(
            event_id="evt-1",
            fault_type="congestion",
            severity=0.8,
            duration_ticks=20,
            remaining_ticks=20,
            affected_devices=["dc-1"],
        )
        assert f.event_id == "evt-1"
        assert f.severity == 0.8
