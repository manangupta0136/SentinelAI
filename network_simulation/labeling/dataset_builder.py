"""Dataset builder that joins telemetry and fault events into
training-ready datasets.

Produces the final CSV and JSON outputs that can be consumed by
downstream ML pipelines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from network_simulation.labeling.ground_truth import GroundTruthLabel
from network_simulation.telemetry.metrics import TelemetryFrame
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class DatasetBuilder:
    """Builds training-ready datasets from telemetry and ground-truth labels.

    The builder can:
        - Enrich telemetry with label columns (supervised learning).
        - Produce separate telemetry and ground-truth files (unsupervised /
          evaluation).
        - Generate summary statistics for dataset quality checks.
    """

    def __init__(self) -> None:
        """Initialise the dataset builder."""
        self._telemetry_df: Optional[pd.DataFrame] = None
        self._labels_df: Optional[pd.DataFrame] = None

    def ingest_telemetry(self, frame: TelemetryFrame) -> None:
        """Ingest a TelemetryFrame for later merging.

        Args:
            frame: TelemetryFrame with one tick of data.
        """
        self._telemetry_df = frame.to_dataframe()

    def ingest_labels(self, labels: List[GroundTruthLabel]) -> None:
        """Ingest ground-truth labels for later merging.

        Args:
            labels: List of GroundTruthLabel instances.
        """
        if not labels:
            self._labels_df = pd.DataFrame()
            return
        self._labels_df = pd.DataFrame([l.to_dict() for l in labels])

    def build_merged_dataset(self) -> pd.DataFrame:
        """Merge telemetry with ground-truth labels on time range.

        Each telemetry record is annotated with the fault type, severity,
        and event_id of any fault that was active at that tick.

        Returns:
            Merged DataFrame with label columns appended to telemetry.
        """
        if self._telemetry_df is None or self._labels_df is None:
            return pd.DataFrame()
        merged = self._telemetry_df.copy()
        merged["has_fault"] = 0
        merged["fault_type"] = ""
        merged["fault_severity"] = 0.0
        merged["fault_event_id"] = ""

        for _, label in self._labels_df.iterrows():
            mask = merged["tick"].between(
                self._tick_from_iso(label["start_time"]),
                self._tick_from_iso(label["end_time"]),
            )
            merged.loc[mask, "has_fault"] = 1
            merged.loc[mask, "fault_type"] = label["fault_type"]
            merged.loc[mask, "fault_severity"] = label["severity"]
            merged.loc[mask, "fault_event_id"] = label["event_id"]

        return merged

    @staticmethod
    def _tick_from_iso(iso_timestamp: str) -> int:
        """Convert an ISO timestamp to a tick number (simple heuristic).

        Args:
            iso_timestamp: ISO 8601 string.

        Returns:
            Approximate tick number.
        """
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            return int(dt.timestamp() // 60)
        except (ValueError, TypeError):
            return 0

    def dataset_summary(self) -> Dict[str, Any]:
        """Return summary statistics for the current datasets.

        Returns:
            Dictionary with row counts, label counts, etc.
        """
        return {
            "telemetry_rows": len(self._telemetry_df)
            if self._telemetry_df is not None
            else 0,
            "label_count": len(self._labels_df)
            if self._labels_df is not None
            else 0,
            "fault_type_distribution": (
                self._labels_df["fault_type"].value_counts().to_dict()
                if self._labels_df is not None
                and not self._labels_df.empty
                else {}
            ),
        }
