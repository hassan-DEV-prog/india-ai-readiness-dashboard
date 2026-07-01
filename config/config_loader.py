"""
Configuration Loader
====================
Single entry point for reading settings.yaml throughout the project.

Design Decision
---------------
Every module imports `get_config()` rather than reading YAML directly.
This means:
  - Config is loaded once and cached (no repeated disk I/O)
  - Path to settings.yaml is resolved relative to this file, so the
    project works regardless of the working directory
  - Switching config files (e.g., for testing) requires changing one line

Usage
-----
    from config.config_loader import get_config

    cfg = get_config()
    raw_path = cfg["paths"]["data_raw"]
"""

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Resolve the settings file path relative to THIS file's location.
# This makes imports work regardless of where the user runs Python from.
_SETTINGS_PATH = Path(__file__).parent / "settings.yaml"


@functools.lru_cache(maxsize=1)
def get_config() -> dict[str, Any]:
    """
    Load and cache the project configuration from settings.yaml.

    Returns
    -------
    dict[str, Any]
        Parsed YAML configuration as a nested dictionary.

    Raises
    ------
    FileNotFoundError
        If settings.yaml does not exist at the expected path.
    yaml.YAMLError
        If settings.yaml contains invalid YAML syntax.

    Notes
    -----
    Uses functools.lru_cache so the file is read only once per
    interpreter session, regardless of how many modules call get_config().
    """
    if not _SETTINGS_PATH.exists():
        raise FileNotFoundError(
            f"Configuration file not found at: {_SETTINGS_PATH}\n"
            "Ensure you are running from the project root directory."
        )

    logger.debug("Loading configuration from: %s", _SETTINGS_PATH)

    with _SETTINGS_PATH.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Configuration file is empty: {_SETTINGS_PATH}")

    logger.info(
        "Configuration loaded successfully. Project: %s v%s",
        config.get("project", {}).get("name", "unknown"),
        config.get("project", {}).get("version", "unknown"),
    )

    return config


def get_project_root() -> Path:
    """
    Return the absolute path to the project root directory.

    The project root is defined as the parent of the config/ directory.
    All relative paths in settings.yaml are resolved against this root.

    Returns
    -------
    Path
        Absolute path to the project root.
    """
    return _SETTINGS_PATH.parent.parent


def resolve_path(relative_path: str) -> Path:
    """
    Resolve a relative path from settings.yaml to an absolute Path.

    Parameters
    ----------
    relative_path : str
        A path string as found in settings.yaml, e.g. "data/raw".

    Returns
    -------
    Path
        Absolute path resolved against the project root.

    Examples
    --------
    >>> from config.config_loader import resolve_path
    >>> resolve_path("data/raw")
    PosixPath('/home/user/india-ai-readiness-dashboard/data/raw')
    """
    return get_project_root() / relative_path
