"""Abstract base class for all fault injectors.

Defines the contract that every fault injector must implement:
    - apply(scheduled_fault)  — inject the fault into the topology
    - recover(scheduled_fault) — remove the fault and restore state
    - serialize() — return injector state as a dictionary
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from network_simulation.monte_carlo.scheduler import ScheduledFault


class FaultInjector(ABC):
    """Abstract base for fault injectors.

    All injectors receive the topology state via dependency injection
    (the NetworkBuilder) rather than reaching into global state.
    """

    @abstractmethod
    def apply(self, fault: ScheduledFault) -> None:
        """Inject a fault into the network topology.

        Args:
            fault: The scheduled fault to apply.
        """
        ...

    @abstractmethod
    def recover(self, fault: ScheduledFault) -> None:
        """Recover from a fault, restoring normal operation.

        Args:
            fault: The fault to recover from.
        """
        ...

    @abstractmethod
    def serialize(self) -> Dict[str, Any]:
        """Return the current state of this injector as a dictionary.

        Returns:
            Serialized injector state.
        """
        ...
