"""Structured logging setup for the simulation framework."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10_485_760,
    backup_count: int = 5,
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
) -> None:
    """Configure the root logger with console and optional rotating file handler.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to a log file for rotating file output.
        max_bytes: Maximum bytes per log file before rotation.
        backup_count: Number of rotated backup files to retain.
        fmt: Log format string.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)

    for handler in root.handlers[:]:
        root.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
