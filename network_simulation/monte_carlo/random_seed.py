"""Random seed manager for reproducible Monte Carlo simulations.

Provides a single source of randomness that can be seeded deterministically
so that all stochastic processes (fault occurrence, severity, duration,
device selection) are reproducible across runs.
"""

from __future__ import annotations

from typing import Optional

import numpy as np


class RandomSeedManager:
    """Manages a global NumPy random generator with deterministic seeding.

    The manager ensures that a single seed produces identical sequences
    of random numbers across simulation runs.
    """

    def __init__(self, seed: int = 42) -> None:
        """Initialise the manager and create a Generator.

        Args:
            seed: Integer seed for reproducibility.
        """
        self._seed = seed
        self._rng: np.random.Generator = np.random.default_rng(seed)

    @property
    def rng(self) -> np.random.Generator:
        """Return the current random generator instance."""
        return self._rng

    def reseed(self, seed: Optional[int] = None) -> None:
        """Re-seed the random generator.

        Args:
            seed: New seed.  If None, uses the original seed.
        """
        self._seed = seed if seed is not None else self._seed
        self._rng = np.random.default_rng(self._seed)

    def spawn(self) -> np.random.Generator:
        """Spawn an independent child generator (for parallel usage).

        Returns:
            A new Generator with an independent stream.
        """
        return self._rng.spawn(1)[0]

    @property
    def seed(self) -> int:
        """Return the current seed."""
        return self._seed
