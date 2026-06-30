"""Fault timeline visualization using matplotlib.

Produces a Gantt-style chart of fault events over the simulation timeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from network_simulation.utils.logger import get_logger

matplotlib.use("Agg")
logger = get_logger(__name__)

_FAULT_COLORS = {
    "congestion": "#E74C3C",
    "bgp_flap": "#3498DB",
    "ospf_failure": "#9B59B6",
    "tunnel_failure": "#E67E22",
    "mpls_failure": "#1ABC9C",
    "link_failure": "#C0392B",
    "controller_error": "#F39C12",
    "cpu_overload": "#D35400",
    "memory_exhaustion": "#8E44AD",
    "packet_loss_escalation": "#2C3E50",
}


class FaultTimelinePlotter:
    """Generates a Gantt-style fault timeline chart."""

    def __init__(
        self, fault_events: List[Dict[str, Any]]
    ) -> None:
        """Initialise the plotter.

        Args:
            fault_events: List of fault event dictionaries with
                event_id, fault_type, severity, start_time, end_time.
        """
        self._events = fault_events

    def plot(
        self,
        output_path: Optional[Path] = None,
        show: bool = False,
    ) -> None:
        """Generate the fault timeline chart.

        Args:
            output_path: If set, save the figure to this path.
            show: Whether to display the plot interactively.
        """
        if not self._events:
            logger.warning("No fault events to plot.")
            return

        fig, ax = plt.subplots(figsize=(14, max(4, len(self._events) * 0.5)))

        for i, event in enumerate(self._events):
            fault_type = event.get("fault_type", "unknown")
            severity = event.get("severity", 0.5)
            color = _FAULT_COLORS.get(fault_type, "#95A5A6")
            alpha = 0.4 + 0.6 * severity
            tick = event.get("tick", 0)
            duration = event.get("duration_ticks", 10)
            ax.barh(
                i,
                duration,
                left=tick,
                height=0.6,
                color=color,
                alpha=alpha,
                edgecolor="black",
                linewidth=0.5,
            )
            ax.text(
                tick + duration / 2,
                i,
                fault_type,
                ha="center",
                va="center",
                fontsize=7,
                fontweight="bold",
                color="white",
            )

        ax.set_xlabel("Simulation Tick")
        ax.set_ylabel("Fault Event")
        ax.set_title("Fault Timeline")
        ax.set_yticks(range(len(self._events)))
        ax.set_yticklabels(
            [e.get("event_id", "")[:8] for e in self._events],
            fontsize=6,
        )
        ax.grid(True, axis="x", alpha=0.3)

        legend_patches = [
            mpatches.Patch(color=color, label=ftype)
            for ftype, color in _FAULT_COLORS.items()
        ]
        ax.legend(
            handles=legend_patches,
            loc="upper right",
            fontsize=6,
            ncol=2,
        )

        plt.tight_layout()

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
            logger.info("Fault timeline saved to %s", output_path)
        if show:
            plt.show()
        plt.close(fig)
