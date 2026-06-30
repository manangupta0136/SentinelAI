#!/usr/bin/env python3
"""Entry point for the Network Simulation and Fault Injection Engine.

Usage:
    python main.py [--config CONFIG_DIR] [--output OUTPUT_DIR]
                   [--ticks N] [--seed S] [--visualize]

Runs a full Monte Carlo simulation of an enterprise MPLS + SD-WAN network,
generates synthetic telemetry, injects faults, and produces labeled datasets
for downstream ML pipelines.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the project root (parent of this package) is on sys.path so that
# ``from network_simulation.xxx import ...`` works when running
# ``python main.py`` directly (instead of via ``python -m``).
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from network_simulation.fault_injection.bgp_flap import BgpFlapInjector
from network_simulation.fault_injection.congestion import CongestionInjector
from network_simulation.fault_injection.controller_error import (
    ControllerErrorInjector,
)
from network_simulation.fault_injection.cpu_overload import CpuOverloadInjector
from network_simulation.fault_injection.memory_exhaustion import (
    MemoryExhaustionInjector,
)
from network_simulation.fault_injection.mpls_failure import MplsFailureInjector
from network_simulation.fault_injection.ospf_failure import OspfFailureInjector
from network_simulation.fault_injection.packet_loss_escalation import (
    PacketLossEscalationInjector,
)
from network_simulation.fault_injection.tunnel_failure import (
    TunnelFailureInjector,
)
from network_simulation.monte_carlo.simulator import MonteCarloSimulator
from network_simulation.utils.constants import FaultType
from network_simulation.utils.logger import get_logger, setup_logging
from network_simulation.visualization.fault_timeline import (
    FaultTimelinePlotter,
)
from network_simulation.visualization.telemetry_dashboard import (
    TelemetryDashboard,
)
from network_simulation.visualization.topology_plot import TopologyPlotter

logger = get_logger(__name__)

_FAULT_INJECTOR_MAP = {
    FaultType.CONGESTION: CongestionInjector,
    FaultType.BGP_FLAP: BgpFlapInjector,
    FaultType.OSPF_FAILURE: OspfFailureInjector,
    FaultType.TUNNEL_FAILURE: TunnelFailureInjector,
    FaultType.MPLS_FAILURE: MplsFailureInjector,
    FaultType.CONTROLLER_ERROR: ControllerErrorInjector,
    FaultType.CPU_OVERLOAD: CpuOverloadInjector,
    FaultType.MEMORY_EXHAUSTION: MemoryExhaustionInjector,
    FaultType.PACKET_LOSS_ESCALATION: PacketLossEscalationInjector,
}


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with simulation parameters.
    """
    parser = argparse.ArgumentParser(
        description="Network Simulation and Monte Carlo Fault Injection Engine",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to the config directory (default: ./config)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to the output directory (default: ./output)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=None,
        help="Override total simulation ticks",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed for reproducibility",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        default=False,
        help="Generate visualization plots after simulation",
    )
    return parser.parse_args(argv)


def register_injectors(simulator: MonteCarloSimulator) -> None:
    """Register all fault injectors with the simulator.

    Uses dependency injection: each injector receives references to the
    network topology and routing engine from the simulator.

    Args:
        simulator: The MonteCarloSimulator instance.
    """
    nb = simulator._network_builder
    re = simulator._routing_engine

    injector_pairs: List[tuple] = [
        (FaultType.CONGESTION, CongestionInjector(nb)),
        (FaultType.BGP_FLAP, BgpFlapInjector(nb, re)),
        (FaultType.OSPF_FAILURE, OspfFailureInjector(nb, re)),
        (FaultType.TUNNEL_FAILURE, TunnelFailureInjector(nb)),
        (FaultType.MPLS_FAILURE, MplsFailureInjector(nb)),
        (FaultType.CONTROLLER_ERROR, ControllerErrorInjector(nb)),
        (FaultType.CPU_OVERLOAD, CpuOverloadInjector(nb)),
        (FaultType.MEMORY_EXHAUSTION, MemoryExhaustionInjector(nb)),
        (
            FaultType.PACKET_LOSS_ESCALATION,
            PacketLossEscalationInjector(nb),
        ),
    ]
    for fault_type, injector in injector_pairs:
        simulator.register_injector(fault_type, injector)

    logger.info("Registered %d fault injectors", len(injector_pairs))


def generate_visualizations(simulator: MonteCarloSimulator) -> None:
    """Generate topology, telemetry, and fault timeline plots.

    Args:
        simulator: The completed simulator instance.
    """
    output_dir = simulator._output_dir

    topology_plotter = TopologyPlotter(simulator._network_builder)
    topology_plotter.plot(output_path=output_dir / "topology.png")
    logger.info("Topology plot saved to %s", output_dir / "topology.png")

    dashboard = TelemetryDashboard(simulator._telemetry_frame)
    dashboard.plot(output_path=output_dir / "telemetry_dashboard.png")
    logger.info(
        "Telemetry dashboard saved to %s",
        output_dir / "telemetry_dashboard.png",
    )

    timeline = FaultTimelinePlotter(simulator._fault_history)
    timeline.plot(output_path=output_dir / "fault_timeline.png")
    logger.info(
        "Fault timeline saved to %s", output_dir / "fault_timeline.png"
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the network simulation pipeline.

    Args:
        argv: Optional argument list (for testing).

    Returns:
        Exit code (0 on success).
    """
    args = parse_args(argv)

    pkg_dir = Path(__file__).parent
    config_dir = (
        Path(args.config) if args.config else pkg_dir / "config"
    )
    output_dir = (
        Path(args.output) if args.output else pkg_dir / "output"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_logging(
        level="INFO",
        log_file=str(output_dir / "simulation.log"),
    )

    logger.info("=" * 60)
    logger.info("SentinelAI Network Simulation Engine")
    logger.info("=" * 60)
    logger.info("Config dir: %s", config_dir)
    logger.info("Output dir: %s", output_dir)

    simulator = MonteCarloSimulator(config_dir, output_dir)

    if args.ticks is not None:
        simulator._total_ticks = args.ticks
    if args.seed is not None:
        simulator._seed_manager.reseed(args.seed)

    register_injectors(simulator)

    summary = simulator.run()

    logger.info("Simulation complete:")
    for key, value in summary.items():
        logger.info("  %s: %s", key, value)

    if args.visualize:
        generate_visualizations(simulator)

    logger.info("Output files written to: %s", output_dir.absolute())
    return 0


if __name__ == "__main__":
    sys.exit(main())
