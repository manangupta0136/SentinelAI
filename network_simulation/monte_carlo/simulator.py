"""Main Monte Carlo simulation orchestrator.

Runs the tick-by-tick loop that drives traffic generation, fault
scheduling, fault injection, telemetry collection, and dataset export.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from network_simulation.fault_injection.injector import FaultInjector
from network_simulation.fault_injection.recovery import RecoveryEngine
from network_simulation.labeling.event_logger import EventLogger
from network_simulation.labeling.ground_truth import GroundTruthLabel
from network_simulation.labeling.dataset_builder import DatasetBuilder
from network_simulation.monte_carlo.distributions import DistributionSampler
from network_simulation.monte_carlo.random_seed import RandomSeedManager
from network_simulation.monte_carlo.scheduler import (
    FaultScheduler,
    ScheduledFault,
)
from network_simulation.telemetry.collector import TelemetryCollector
from network_simulation.telemetry.exporters import TelemetryExporter
from network_simulation.telemetry.metrics import TelemetryFrame
from network_simulation.telemetry.timestamp import SimulationTimestamp
from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.topology.routing import RoutingEngine
from network_simulation.traffic.traffic_generator import TrafficGenerator
from network_simulation.utils.helpers import load_yaml_config
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class MonteCarloSimulator:
    """Orchestrates the full simulation lifecycle.

    Coordinates network topology, traffic generation, Monte Carlo fault
    scheduling, fault injection, telemetry collection, and dataset export.
    """

    def __init__(
        self,
        config_dir: Path,
        output_dir: Optional[Path] = None,
    ) -> None:
        """Initialise the simulator from YAML configuration.

        Args:
            config_dir: Directory containing network.yaml, simulation.yaml,
                traffic.yaml, and faults.yaml.
            output_dir: Output directory for datasets.  Defaults to
                ``config_dir / ".." / "output"``.
        """
        self._config_dir = Path(config_dir)
        self._output_dir = (
            Path(output_dir) if output_dir else self._config_dir / ".." / "output"
        )
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._sim_config = load_yaml_config(self._config_dir / "simulation.yaml")
        self._faults_config = load_yaml_config(self._config_dir / "faults.yaml")

        seed = self._sim_config.get("simulation", {}).get("random_seed", 42)
        self._seed_manager = RandomSeedManager(seed)
        self._rng = self._seed_manager.rng
        self._sampler = DistributionSampler(self._rng)

        self._network_builder = NetworkBuilder(
            self._config_dir / "network.yaml"
        )
        self._graph = self._network_builder.graph
        self._routing_engine = RoutingEngine(self._graph)

        self._traffic_generator = TrafficGenerator(
            self._network_builder,
            self._config_dir / "traffic.yaml",
            self._rng,
        )

        self._fault_scheduler = FaultScheduler(
            self._faults_config,
            self._graph,
            self._sampler,
            self._seed_manager,
        )

        self._injectors: Dict[str, FaultInjector] = {}
        self._recovery_engine = RecoveryEngine(self._network_builder)
        self._event_logger = EventLogger()
        self._telemetry_collector = TelemetryCollector(
            self._network_builder, self._routing_engine
        )
        self._telemetry_frame = TelemetryFrame()
        self._exporter = TelemetryExporter(self._output_dir)
        self._dataset_builder = DatasetBuilder()

        self._current_tick: int = 0
        self._current_time: datetime = datetime(
            1970, 1, 1, tzinfo=timezone.utc
        )
        self._tick_interval = (
            self._sim_config.get("simulation", {})
            .get("tick_interval_seconds", 60)
        )
        self._total_ticks = (
            self._sim_config.get("simulation", {}).get("total_ticks", 1440)
        )
        self._fault_history: List[Dict[str, Any]] = []

    def register_injector(
        self, fault_type: str, injector: FaultInjector
    ) -> None:
        """Register a fault injector for a given fault type.

        Args:
            fault_type: Fault type string (from FaultType constants).
            injector: Injector instance implementing FaultInjector.
        """
        self._injectors[fault_type] = injector
        logger.debug("Registered injector for fault type: %s", fault_type)

    def run(self) -> Dict[str, Any]:
        """Run the full simulation.

        Returns:
            Summary dictionary with tick count, fault count, etc.
        """
        logger.info(
            "Starting simulation: %d ticks, interval=%ds, seed=%d",
            self._total_ticks,
            self._tick_interval,
            self._seed_manager.seed,
        )

        for tick in range(self._total_ticks):
            self._current_tick = tick
            self._current_time = datetime.fromtimestamp(
                tick * self._tick_interval, tz=timezone.utc
            )
            self._step()

        self._finalize()
        summary = self._build_summary()
        logger.info("Simulation complete: %s", summary)
        return summary

    def _step(self) -> None:
        """Execute one simulation tick."""
        self._traffic_generator.update(self._current_time)
        self._routing_engine.recompute_all()

        scheduled = self._fault_scheduler.tick(self._current_tick)
        if scheduled is not None:
            self._apply_fault(scheduled)

        self._process_active_faults()

        timestamp = SimulationTimestamp(
            tick=self._current_tick,
            wall_clock=self._current_time,
            tick_interval_seconds=self._tick_interval,
        )
        records = self._telemetry_collector.collect(timestamp)
        self._telemetry_frame.extend(records)

    def _apply_fault(self, scheduled: ScheduledFault) -> None:
        """Apply a scheduled fault using the registered injector.

        Args:
            scheduled: The fault to apply.
        """
        injector = self._injectors.get(scheduled.fault_type)
        if injector is None:
            logger.warning(
                "No injector registered for fault type: %s",
                scheduled.fault_type,
            )
            return
        injector.apply(scheduled)
        self._event_logger.log_fault_start(
            scheduled, self._current_time.isoformat()
        )
        self._fault_history.append(scheduled.__dict__)

    def _process_active_faults(self) -> None:
        """Process all active faults — apply ongoing effects or recover."""
        for fault in self._fault_scheduler.active_faults:
            injector = self._injectors.get(fault.fault_type)
            if injector is None:
                continue
            if fault.remaining_ticks <= 1:
                injector.recover(fault)
                self._recovery_engine.recover(fault)
                self._event_logger.log_fault_end(
                    fault, self._current_time.isoformat()
                )
            else:
                injector.apply(fault)

    def _finalize(self) -> None:
        """Export all datasets and metadata."""
        labels = self._event_logger.get_labels()
        fault_events = [f for f in self._fault_history]
        sim_params = self._sim_config.get("simulation", {})

        self._exporter.export_telemetry_csv(self._telemetry_frame)
        self._exporter.export_telemetry_json(self._telemetry_frame)

        gt_records = [label.to_dict() for label in labels]
        self._exporter.export_ground_truth_csv(gt_records)
        self._exporter.export_fault_events_json(fault_events)

        summary = self._build_summary()
        self._exporter.export_simulation_summary(summary)

        metadata = {
            "simulation_parameters": sim_params,
            "network_topology": self._network_builder.to_dict(),
            "fault_config": self._faults_config,
            "tick_count": self._current_tick + 1,
            "fault_count": len(self._fault_history),
            "telemetry_record_count": self._telemetry_frame.size,
            "seed": self._seed_manager.seed,
        }
        self._exporter.export_metadata(metadata)

    def _build_summary(self) -> Dict[str, Any]:
        """Build the simulation summary dictionary.

        Returns:
            Summary with counts, duration, and fault statistics.
        """
        return {
            "total_ticks": self._current_tick + 1,
            "tick_interval_seconds": self._tick_interval,
            "total_faults_injected": len(self._fault_history),
            "telemetry_records": self._telemetry_frame.size,
            "fault_type_counts": self._count_fault_types(),
            "seed": self._seed_manager.seed,
            "network_devices": self._graph.number_of_nodes(),
            "network_links": self._graph.number_of_edges(),
            "network_tunnels": len(self._network_builder.tunnels),
        }

    def _count_fault_types(self) -> Dict[str, int]:
        """Count faults by type.

        Returns:
            Dictionary mapping fault type to count.
        """
        counts: Dict[str, int] = {}
        for f in self._fault_history:
            ft = f.get("fault_type", "unknown")
            counts[ft] = counts.get(ft, 0) + 1
        return counts
