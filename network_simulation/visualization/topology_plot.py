"""Topology visualization using matplotlib and networkx.

Produces a static plot of the network topology annotated with device
roles and link statuses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import networkx as nx

from network_simulation.topology.network_builder import NetworkBuilder
from network_simulation.utils.constants import LinkStatus
from network_simulation.utils.logger import get_logger

matplotlib.use("Agg")
logger = get_logger(__name__)


class TopologyPlotter:
    """Plots the network topology graph with role-based colouring."""

    ROLE_COLORS = {
        "datacenter": "#E74C3C",
        "mpls_hub": "#3498DB",
        "branch": "#2ECC71",
    }

    def __init__(self, network_builder: NetworkBuilder) -> None:
        """Initialise the plotter.

        Args:
            network_builder: Built network topology.
        """
        self._network = network_builder

    def plot(
        self,
        output_path: Optional[Path] = None,
        show: bool = False,
    ) -> None:
        """Generate and optionally save the topology plot.

        Args:
            output_path: If set, save the figure to this path.
            show: Whether to display the plot interactively.
        """
        graph = self._network.graph
        pos = nx.spring_layout(graph, seed=42)

        fig, ax = plt.subplots(figsize=(12, 8))

        node_colors = []
        for node, data in graph.nodes(data=True):
            device = data.get("device")
            if device:
                node_colors.append(
                    self.ROLE_COLORS.get(device.role, "#95A5A6")
                )
            else:
                node_colors.append("#95A5A6")

        nx.draw_networkx_nodes(
            graph, pos, ax=ax, node_color=node_colors,
            node_size=800, edgecolors="black",
        )
        nx.draw_networkx_labels(graph, pos, ax=ax, font_size=8)

        edge_colors = []
        for _, _, data in graph.edges(data=True):
            link = data.get("link")
            if link is None:
                edge_colors.append("gray")
            elif link.status == LinkStatus.DOWN:
                edge_colors.append("red")
            elif link.status == LinkStatus.DEGRADED:
                edge_colors.append("orange")
            else:
                edge_colors.append("green")
        nx.draw_networkx_edges(
            graph, pos, ax=ax, edge_color=edge_colors,
            arrows=True, arrowsize=15,
        )

        ax.set_title("Network Topology", fontsize=14)
        ax.axis("off")

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
            logger.info("Topology plot saved to %s", output_path)
        if show:
            plt.show()
        plt.close(fig)
