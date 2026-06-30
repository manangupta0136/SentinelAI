"""Telemetry dashboard visualization using matplotlib.

Produces a multi-panel figure showing key telemetry metrics over time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

from network_simulation.telemetry.metrics import TelemetryFrame
from network_simulation.utils.logger import get_logger

matplotlib.use("Agg")
logger = get_logger(__name__)


class TelemetryDashboard:
    """Generates a multi-panel dashboard plot of telemetry metrics."""

    def __init__(self, frame: TelemetryFrame) -> None:
        """Initialise the dashboard.

        Args:
            frame: TelemetryFrame with all tick data.
        """
        self._df = frame.to_dataframe()

    def plot(
        self,
        output_path: Optional[Path] = None,
        show: bool = False,
    ) -> None:
        """Generate the dashboard figure.

        Args:
            output_path: If set, save the figure to this path.
            show: Whether to display the plot interactively.
        """
        if self._df.empty:
            logger.warning("No telemetry data to plot.")
            return

        fig, axes = plt.subplots(3, 2, figsize=(16, 10))
        fig.suptitle("Telemetry Dashboard", fontsize=14)

        device_df = self._df[self._df["record_type"] == "device"]
        link_df = self._df[self._df["record_type"] == "link"]

        if not device_df.empty:
            self._plot_metric(
                axes[0, 0], device_df, "tick", "cpu_utilization",
                "CPU Utilization (%)", "cpu_utilization",
            )
            self._plot_metric(
                axes[0, 1], device_df, "tick", "memory_utilization",
                "Memory Utilization (%)", "memory_utilization",
            )
            self._plot_metric(
                axes[1, 0], device_df, "tick", "cpu_temperature",
                "CPU Temperature (C)", "cpu_temperature",
            )

        if not link_df.empty:
            self._plot_metric(
                axes[1, 1], link_df, "tick", "latency_ms",
                "Latency (ms)", "latency_ms",
            )
            self._plot_metric(
                axes[2, 0], link_df, "tick", "packet_loss",
                "Packet Loss", "packet_loss",
            )
            self._plot_metric(
                axes[2, 1], link_df, "tick", "bandwidth_utilization",
                "Bandwidth Utilization", "bandwidth_utilization",
            )

        plt.tight_layout()

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
            logger.info("Telemetry dashboard saved to %s", output_path)
        if show:
            plt.show()
        plt.close(fig)

    @staticmethod
    def _plot_metric(
        ax: plt.Axes,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        ylabel: str,
        legend_label: str,
    ) -> None:
        """Plot one metric onto an axis.

        Args:
            ax: Matplotlib axis.
            df: DataFrame with data.
            x_col: Column name for x-axis.
            y_col: Column name for y-axis.
            ylabel: Y-axis label.
            legend_label: Legend label.
        """
        if df.empty or y_col not in df.columns:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return
        device_names = df["device_name"].unique()
        for dev in device_names[:5]:
            subset = df[df["device_name"] == dev]
            subset = subset.sort_values(x_col)
            ax.plot(
                subset[x_col], subset[y_col],
                label=dev, alpha=0.7, linewidth=0.8,
            )
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Tick")
        ax.legend(fontsize=6, loc="best")
        ax.grid(True, alpha=0.3)
