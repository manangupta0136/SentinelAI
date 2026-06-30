"""Fault scheduler that determines when faults occur during the simulation.

At each tick, uses Monte Carlo sampling to decide whether a new fault
should be injected, which type, at what severity, and on which devices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx
import numpy as np

from network_simulation.monte_carlo.distributions import DistributionSampler
from network_simulation.monte_carlo.random_seed import RandomSeedManager
from network_simulation.utils.constants import FaultType
from network_simulation.utils.helpers import generate_event_id
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScheduledFault:
    """Represents a fault event scheduled or active in the simulation.

    Attributes:
        event_id: Unique identifier for this fault event.
        fault_type: Type of fault (from FaultType constants).
        severity: Severity level (0–1).
        duration_ticks: Total duration in ticks.
        remaining_ticks: Ticks remaining before recovery.
        affected_devices: List of device names affected.
        affected_links: List of link IDs affected.
        recovery_method: Method used for recovery.
        params: Additional fault-type-specific parameters.
    """

    event_id: str = ""
    fault_type: str = ""
    severity: float = 0.5
    duration_ticks: int = 10
    remaining_ticks: int = 10
    affected_devices: List[str] = field(default_factory=list)
    affected_links: List[str] = field(default_factory=list)
    recovery_method: str = "automatic"
    params: Dict[str, Any] = field(default_factory=dict)


class FaultScheduler:
    """Monte Carlo scheduler that decides when and what faults to inject.

    At each tick, the scheduler may generate a ScheduledFault based on
    configurable probabilities and distributions.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        graph: nx.DiGraph,
        sampler: DistributionSampler,
        seed_manager: RandomSeedManager,
    ) -> None:
        """Initialise the fault scheduler.

        Args:
            config: Faults configuration (from faults.yaml).
            graph: NetworkX topology graph.
            sampler: DistributionSampler for stochastic decisions.
            seed_manager: RandomSeedManager for reproducibility.
        """
        self._config = config
        self._graph = graph
        self._sampler = sampler
        self._rng = seed_manager.rng
        self._active_faults: List[ScheduledFault] = []
        self._last_fault_tick: int = -100
        self._fault_prob = config.get("monte_carlo", {}).get(
            "fault_probability_per_tick", 0.02
        )
        self._max_concurrent = config.get("monte_carlo", {}).get(
            "max_concurrent_faults", 3
        )
        self._min_ticks_between = config.get("monte_carlo", {}).get(
            "min_ticks_between_faults", 10
        )
        self._type_weights = config.get("monte_carlo", {}).get(
            "fault_type_weights", {}
        )

    def tick(self, current_tick: int) -> Optional[ScheduledFault]:
        """Evaluate one tick and return a new fault if one should occur.

        Also decrements remaining ticks on active faults.

        Args:
            current_tick: Current simulation tick number.

        Returns:
            A ScheduledFault if a new fault is triggered, else None.
        """
        self._decrement_active()
        if len(self._active_faults) >= self._max_concurrent:
            return None
        if current_tick - self._last_fault_tick < self._min_ticks_between:
            return None
        if not self._sampler.sample_bool(self._fault_prob):
            return None
        fault = self._create_fault(current_tick)
        self._active_faults.append(fault)
        self._last_fault_tick = current_tick
        logger.info(
            "Fault scheduled: type=%s severity=%.2f duration=%d devices=%s",
            fault.fault_type,
            fault.severity,
            fault.duration_ticks,
            fault.affected_devices,
        )
        return fault

    def _decrement_active(self) -> None:
        """Remove faults that have expired."""
        remaining = []
        for fault in self._active_faults:
            fault.remaining_ticks -= 1
            if fault.remaining_ticks > 0:
                remaining.append(fault)
        self._active_faults = remaining

    def _create_fault(self, tick: int) -> ScheduledFault:
        """Create a new ScheduledFault using Monte Carlo sampling.

        Args:
            tick: Current tick number.

        Returns:
            A populated ScheduledFault.
        """
        fault_type = self._sample_fault_type()
        ft_config = self._config.get("fault_types", {}).get(fault_type, {})
        dists = self._config.get("distributions", {})
        severity = self._sampler.sample(dists.get("severity", {}))
        duration = int(
            self._sampler.sample(dists.get("duration_ticks", {}))
        )
        devices, links = self._sample_affected(dists.get("device_selection", {}))
        recovery_method = self._sample_recovery_method(ft_config)
        event_id = generate_event_id()
        return ScheduledFault(
            event_id=event_id,
            fault_type=fault_type,
            severity=severity,
            duration_ticks=duration,
            remaining_ticks=duration,
            affected_devices=devices,
            affected_links=links,
            recovery_method=recovery_method,
            params=self._build_params(ft_config),
        )

    def _sample_fault_type(self) -> str:
        """Sample a fault type from the configured categorical weights.

        Returns:
            Fault type string.
        """
        types = list(self._type_weights.keys())
        weights = list(self._type_weights.values())
        return self._sampler.sample_choice(types, weights)

    def _sample_affected(
        self, device_config: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Sample affected devices and links from the topology.

        Args:
            device_config: Device selection distribution config.

        Returns:
            Tuple of (device_names, link_ids).
        """
        nodes = list(self._graph.nodes())
        if not nodes:
            return [], []
        count = self._sampler.sample_count(
            device_config.get("count_min", 1),
            device_config.get("count_max", 1),
        )
        count = min(count, len(nodes))
        selected = list(self._rng.choice(nodes, size=count, replace=False))
        links = []
        for u, v, data in self._graph.edges(data=True):
            if u in selected or v in selected:
                links.append(data["link"].link_id)
        return selected, links

    def _sample_recovery_method(
        self, ft_config: Dict[str, Any]
    ) -> str:
        """Sample a recovery method for the given fault type config.

        Args:
            ft_config: Fault-type-specific configuration.

        Returns:
            Recovery method string.
        """
        methods = ft_config.get("recovery_methods", ["automatic"])
        return str(self._rng.choice(methods))

    def _build_params(self, ft_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build fault-type-specific parameters from config ranges.

        Args:
            ft_config: Fault-type configuration.

        Returns:
            Parameter dictionary with sampled values from ranges.
        """
        params = {}
        for key, value in ft_config.items():
            if isinstance(value, list) and len(value) == 2:
                try:
                    params[key] = float(
                        self._rng.uniform(value[0], value[1])
                    )
                except (TypeError, ValueError):
                    params[key] = value
        return params

    @property
    def active_faults(self) -> List[ScheduledFault]:
        """Return the list of currently active faults."""
        return list(self._active_faults)
