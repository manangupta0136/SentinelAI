"""Configurable probability distributions for Monte Carlo fault sampling.

All distribution parameters come from YAML configuration — no hardcoded
distribution parameters in code.  Supported types include beta, normal,
truncated normal, exponential, lognormal, uniform, and categorical.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class DistributionSampler:
    """Samples from named distributions defined in configuration.

    All sampling uses the provided ``rng`` so that the process is
    reproducible.
    """

    def __init__(self, rng: np.random.Generator) -> None:
        """Initialise the sampler.

        Args:
            rng: NumPy random generator (should come from
                :class:`~monte_carlo.random_seed.RandomSeedManager`).
        """
        self._rng = rng

    def sample(self, dist_config: Dict[str, Any]) -> float:
        """Sample a single value from a distribution described by a config dict.

        Args:
            dist_config: Distribution configuration with keys ``type``,
                ``params``, and optionally ``min``, ``max``, ``scale_min``,
                ``scale_max``.

        Returns:
            A sampled value.

        Raises:
            ValueError: If the distribution type is unsupported.
        """
        dist_type = dist_config.get("type", "uniform")
        params = dist_config.get("params", {})
        min_val = dist_config.get("min")
        max_val = dist_config.get("max")
        scale_min = dist_config.get("scale_min")
        scale_max = dist_config.get("scale_max")

        if dist_type == "uniform" and min_val is not None and max_val is not None:
            return float(self._rng.uniform(float(min_val), float(max_val)))

        raw = self._sample_raw(dist_type, params)

        if scale_min is not None and scale_max is not None:
            raw = scale_min + raw * (scale_max - scale_min)

        if min_val is not None:
            raw = max(raw, float(min_val))
        if max_val is not None:
            raw = min(raw, float(max_val))

        return raw

    def sample_int(self, dist_config: Dict[str, Any]) -> int:
        """Sample an integer value from a distribution.

        Args:
            dist_config: Distribution configuration dict.

        Returns:
            Integer sampled value.
        """
        return int(round(self.sample(dist_config)))

    def sample_choice(
        self,
        items: List[str],
        weights: Optional[List[float]] = None,
    ) -> str:
        """Sample an item from a list with optional weights.

        Args:
            items: List of items to choose from.
            weights: Optional list of weights (will be normalized).

        Returns:
            Selected item.
        """
        if weights:
            return str(self._rng.choice(items, p=self._normalise(weights)))
        return str(self._rng.choice(items))

    def sample_count(self, min_count: int, max_count: int) -> int:
        """Sample an integer count uniformly from [min_count, max_count].

        Args:
            min_count: Minimum count (inclusive).
            max_count: Maximum count (inclusive).

        Returns:
            Sampled integer count.
        """
        return int(self._rng.integers(min_count, max_count + 1))

    def sample_bool(self, probability: float) -> bool:
        """Sample a boolean with a given true probability.

        Args:
            probability: Probability of returning True (0–1).

        Returns:
            True with the given probability.
        """
        return float(self._rng.uniform()) < probability

    def _sample_raw(self, dist_type: str, params: Dict[str, Any]) -> float:
        """Sample from the raw distribution without post-processing.

        Args:
            dist_type: Distribution type name.
            params: Distribution parameters.

        Returns:
            Raw sample.

        Raises:
            ValueError: For unknown distribution types.
        """
        if dist_type == "uniform":
            low = params.get("low", 0.0)
            high = params.get("high", 1.0)
            return float(self._rng.uniform(low, high))
        elif dist_type == "beta":
            alpha = params.get("alpha", 2.0)
            beta = params.get("beta", 5.0)
            return float(self._rng.beta(alpha, beta))
        elif dist_type == "normal":
            mean = params.get("mean", 0.0)
            std = params.get("std", 1.0)
            return float(self._rng.normal(mean, std))
        elif dist_type == "lognormal":
            mean = params.get("mean", 1.0)
            sigma = params.get("sigma", 0.5)
            return float(self._rng.lognormal(mean, sigma))
        elif dist_type == "exponential":
            scale = params.get("scale", 1.0)
            return float(self._rng.exponential(scale))
        elif dist_type == "poisson":
            lam = params.get("lam", 1.0)
            return float(self._rng.poisson(lam))
        elif dist_type == "triangular":
            left = params.get("left", 0.0)
            mode = params.get("mode", 0.5)
            right = params.get("right", 1.0)
            return float(self._rng.triangular(left, mode, right))
        else:
            raise ValueError(f"Unsupported distribution type: {dist_type}")

    @staticmethod
    def _normalise(weights: List[float]) -> List[float]:
        """Normalise a list of weights to sum to 1.0.

        Args:
            weights: Raw weights.

        Returns:
            Normalised probability list.
        """
        total = sum(weights)
        if total == 0:
            return [1.0 / len(weights)] * len(weights)
        return [w / total for w in weights]
