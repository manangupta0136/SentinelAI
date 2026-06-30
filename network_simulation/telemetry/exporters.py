"""Export telemetry and fault data to CSV and JSON formats.

Uses a common pandas DataFrame schema so both formats stay in sync.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from network_simulation.telemetry.metrics import TelemetryFrame
from network_simulation.utils.logger import get_logger

logger = get_logger(__name__)


class TelemetryExporter:
    """Exports simulation output to CSV, JSON, and summary files.

    All export methods accept a pandas DataFrame or TelemetryFrame so
    the caller controls what gets written.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialise the exporter.

        Args:
            output_dir: Directory where output files are written.
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_telemetry_csv(
        self,
        frame: TelemetryFrame,
        filename: str = "telemetry.csv",
    ) -> Path:
        """Export telemetry records to a CSV file.

        Args:
            frame: TelemetryFrame to export.
            filename: Output file name.

        Returns:
            Path to the written CSV file.
        """
        df = frame.to_dataframe()
        path = self._output_dir / filename
        df.to_csv(path, index=False)
        logger.info("Exported %d telemetry rows to %s", len(df), path)
        return path

    def export_telemetry_json(
        self,
        frame: TelemetryFrame,
        filename: str = "telemetry.json",
    ) -> Path:
        """Export telemetry records to a JSON file.

        Args:
            frame: TelemetryFrame to export.
            filename: Output file name.

        Returns:
            Path to the written JSON file.
        """
        records = [r.to_dict() for r in frame.records]
        path = self._output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        logger.info("Exported %d telemetry records to %s", len(records), path)
        return path

    def export_ground_truth_csv(
        self,
        records: List[Dict[str, Any]],
        filename: str = "ground_truth.csv",
    ) -> Path:
        """Export ground truth labels to CSV.

        Args:
            records: List of ground truth label dictionaries.
            filename: Output file name.

        Returns:
            Path to the written CSV file.
        """
        df = pd.DataFrame(records) if records else pd.DataFrame()
        path = self._output_dir / filename
        df.to_csv(path, index=False)
        logger.info("Exported %d ground truth rows to %s", len(df), path)
        return path

    def export_fault_events_json(
        self,
        events: List[Dict[str, Any]],
        filename: str = "fault_events.json",
    ) -> Path:
        """Export fault events to JSON.

        Args:
            events: List of fault event dictionaries.
            filename: Output file name.

        Returns:
            Path to the written JSON file.
        """
        path = self._output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        logger.info("Exported %d fault events to %s", len(events), path)
        return path

    def export_simulation_summary(
        self,
        summary: Dict[str, Any],
        filename: str = "simulation_summary.json",
    ) -> Path:
        """Export simulation summary to JSON.

        Args:
            summary: Summary dictionary.
            filename: Output file name.

        Returns:
            Path to the written JSON file.
        """
        path = self._output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        logger.info("Exported simulation summary to %s", path)
        return path

    def export_metadata(
        self,
        metadata: Dict[str, Any],
        filename: str = "metadata.json",
    ) -> Path:
        """Export simulation metadata to JSON.

        Args:
            metadata: Metadata dictionary.
            filename: Output file name.

        Returns:
            Path to the written JSON file.
        """
        path = self._output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        logger.info("Exported metadata to %s", path)
        return path
