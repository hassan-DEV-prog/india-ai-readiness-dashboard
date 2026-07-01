"""
Logging Configuration
=====================
Centralized logging setup for the India AI Readiness Dashboard project.

Design Decision
---------------
All modules call `get_logger(__name__)` instead of configuring logging
themselves. This means:
  - Log format is consistent across the entire project
  - Switching from file to cloud logging requires changing one file
  - Log level is controlled from settings.yaml, not scattered in code

Usage
-----
    from src.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Starting ETL pipeline...")
    logger.warning("Missing values detected in column: %s", col_name)
    logger.error("Failed to load file: %s", exc, exc_info=True)
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Internal import — safe because logger.py has no project dependencies
from config.config_loader import get_config, get_project_root

_logging_configured = False


def setup_logging() -> None:
    """
    Configure the root logger based on settings.yaml.

    Called ONCE at application startup (app.py or the ETL entry point).
    Subsequent calls are no-ops (idempotent).

    Sets up:
    - Console handler (always)
    - Rotating file handler (if log_to_file is True in config)
    """
    global _logging_configured
    if _logging_configured:
        return

    cfg = get_config()["logging"]
    root = get_project_root()

    level = getattr(logging, cfg["level"].upper(), logging.INFO)
    fmt = cfg["format"]
    datefmt = cfg["datefmt"]
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # ── Console Handler ──────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ── Rotating File Handler ────────────────────────────────
    if cfg.get("log_to_file", False):
        log_path = root / cfg["log_filename"]
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_path,
            maxBytes=cfg.get("max_bytes", 5_242_880),    # 5 MB default
            backupCount=cfg.get("backup_count", 3),
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _logging_configured = True
    root_logger.info(
        "Logging initialized | level=%s | file=%s",
        cfg["level"],
        cfg.get("log_filename", "disabled"),
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a named logger, ensuring project-wide logging is configured.

    Parameters
    ----------
    name : str, optional
        Logger name, conventionally __name__ from the calling module.
        If None, returns the root logger.

    Returns
    -------
    logging.Logger
        Configured logger instance.

    Examples
    --------
    >>> logger = get_logger(__name__)
    >>> logger.info("ETL pipeline started")
    2024-01-15 10:30:00 | INFO     | src.etl.loader | ETL pipeline started
    """
    setup_logging()
    return logging.getLogger(name)
