"""Helper utilities for configuration loading, math, and time handling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml


def load_yaml_config(path: Path) -> Dict[str, Any]:
    """Load and return a YAML configuration file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file contains invalid YAML.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def interpolate_time_of_day(
    hour: float, profile: List[Dict[str, float]]
) -> float:
    """Interpolate a time-of-day multiplier from a piecewise profile.

    The profile is a list of ``{"hour": int, "multiplier": float}`` entries
    sorted by hour. Linear interpolation is used between entries, with
    wraparound at midnight.

    Args:
        hour: Current hour of day (0–24).
        profile: Time-of-day profile as a list of hour/multiplier pairs.

    Returns:
        Interpolated multiplier at the given hour.
    """
    if not profile:
        return 1.0
    sorted_profile = sorted(profile, key=lambda p: p["hour"])
    hours = [p["hour"] for p in sorted_profile]
    multipliers = [p["multiplier"] for p in sorted_profile]
    if hour <= hours[0] or hour >= hours[-1]:
        return float(np.interp(hour, hours, multipliers, period=24.0))
    return float(np.interp(hour, hours, multipliers))


def truncate_normal(
    mean: float,
    std: float,
    lower: float,
    upper: float,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Sample from a truncated normal distribution.

    Args:
        mean: Distribution mean.
        std: Distribution standard deviation.
        lower: Lower bound for truncation.
        upper: Upper bound for truncation.
        rng: NumPy random generator (uses default if None).

    Returns:
        A single sample from the truncated normal distribution.
    """
    if rng is None:
        rng = np.random.default_rng()
    sample = rng.normal(mean, std)
    return float(clamp(sample, lower, upper))


def clamp(value: float, lower: float, upper: float) -> float:
    """Constrain a value within the inclusive interval [lower, upper].

    Args:
        value: Input value.
        lower: Lower bound.
        upper: Upper bound.

    Returns:
        Clamped value.
    """
    return max(lower, min(value, upper))


def generate_event_id() -> str:
    """Generate a unique event identifier.

    Returns:
        A compact UUID4 hex string.
    """
    return uuid.uuid4().hex[:16]


def is_weekend(dt: datetime) -> bool:
    """Check if a datetime falls on a weekend (Saturday or Sunday).

    Args:
        dt: Datetime to check.

    Returns:
        True if the day is Saturday (5) or Sunday (6).
    """
    return dt.weekday() >= 5


def seconds_since_midnight(dt: datetime) -> float:
    """Return the number of seconds since midnight for a given datetime.

    Args:
        dt: Datetime to evaluate.

    Returns:
        Seconds since the most recent midnight.
    """
    return (
        dt - dt.replace(hour=0, minute=0, second=0, microsecond=0)
    ).total_seconds()
