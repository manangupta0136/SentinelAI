"""Network Simulation and Monte Carlo Fault Injection Engine.

An air-gapped predictive copilot module that generates realistic
synthetic network telemetry and labeled fault scenarios.
"""

from network_simulation import (
    config,
    topology,
    traffic,
    telemetry,
    monte_carlo,
    fault_injection,
    labeling,
    visualization,
    utils,
)

__all__ = [
    "config",
    "topology",
    "traffic",
    "telemetry",
    "monte_carlo",
    "fault_injection",
    "labeling",
    "visualization",
    "utils",
]
