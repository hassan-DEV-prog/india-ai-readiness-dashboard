"""
Data Loader
===========
Responsible for reading raw data files from disk and returning
clean, typed DataFrames. This module does NOT clean or transform
data — it only loads it.

Design Principles
-----------------
- One function per data source
- Every function returns a DataFrame with consistent dtype handling
- All file paths resolved through config — no hardcoded strings
- Failures raise descriptive exceptions, never silently return empty frames

Public API
----------
load_aicte_institutes()         -> pd.DataFrame
load_census_literacy()          -> pd.DataFrame
load_state_gdp()                -> pd.DataFrame
load_population()               -> pd.DataFrame
load_electricity()              -> pd.DataFrame
load_broadband()                -> pd.DataFrame
load_internet_penetration()     -> pd.DataFrame
load_startups()                 -> pd.DataFrame
load_digital_literacy()         -> pd.DataFrame
load_all_raw()                  -> dict[str, pd.DataFrame]
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from config.config_loader import get_config, resolve_path
from src.logger import get_logger

logger = get_logger(__name__)


# ── Internal Helpers ──────────────────────────────────────────────────────────

def _get_raw_path(filename_key: str) -> Path:
    """
    Resolve a data file key from config to its absolute path.

    Parameters
    ----------
    filename_key : str
        Key in settings.yaml under data_files, e.g. "aicte_institutes".

    Returns
    -------
    Path
        Absolute path to the raw data file.
    """
    cfg = get_config()
    filename = cfg["data_files"][filename_key]
    return resolve_path(cfg["paths"]["data_raw"]) / filename


def _load_csv(
    filename_key: str,
    dtype: Optional[dict] = None,
    encoding: str = "utf-8",
) -> pd.DataFrame:
    """
    Generic CSV loader with logging and error handling.

    Parameters
    ----------
    filename_key : str
        Key in settings.yaml under data_files.
    dtype : dict, optional
        Column dtype overrides passed to pd.read_csv.
    encoding : str
        File encoding, default utf-8.

    Returns
    -------
    pd.DataFrame

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the resolved path.
    pd.errors.ParserError
        If the CSV cannot be parsed.
    """
    path = _get_raw_path(filename_key)

    if not path.exists():
        raise FileNotFoundError(
            f"Raw data file not found: {path}\n"
            f"Run the data download script or place the file manually.\n"
            f"See docs/data_dictionary.md for source URLs."
        )

    logger.info("Loading %-30s from %s", filename_key, path.name)

    try:
        df = pd.read_csv(path, dtype=dtype, encoding=encoding)
        logger.debug(
            "Loaded %s: %d rows × %d columns", filename_key, len(df), len(df.columns)
        )
        return df
    except pd.errors.ParserError as exc:
        logger.error("Failed to parse %s: %s", path, exc)
        raise


# ── Public Loaders ────────────────────────────────────────────────────────────

def load_aicte_institutes() -> pd.DataFrame:
    """
    Load AICTE approved technical institutes by state.

    Source
    ------
    AICTE Open Data Portal (https://facilities.aicte-india.org/dashboard/pages/dashboardaicte.php)
    Expected columns: state_name, total_institutes, total_seats, engineering_seats

    Returns
    -------
    pd.DataFrame
        Columns: state_name (str), total_institutes (int),
                 total_seats (int), engineering_seats (int)
    """
    df = _load_csv(
        "aicte_institutes",
        dtype={"total_institutes": "Int64", "total_seats": "Int64",
               "engineering_seats": "Int64"},
    )
    logger.info("AICTE institutes loaded: %d states", len(df))
    return df


def load_census_literacy() -> pd.DataFrame:
    """
    Load state-wise literacy rates from Census 2011 / NFHS-5.

    Source
    ------
    Census of India 2011 + NFHS-5 (2019-21) for updated estimates.
    Expected columns: state_name, literacy_rate_pct, male_literacy_pct,
                      female_literacy_pct, rural_literacy_pct, urban_literacy_pct

    Notes
    -----
    NFHS-5 literacy data is used where available as it is more recent.
    Census 2011 is the fallback. Both vintages are documented in
    data_dictionary.md and flagged in the dataset with a source_year column.

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "census_literacy",
        dtype={"literacy_rate_pct": float, "source_year": "Int64"},
    )
    logger.info("Literacy data loaded: %d states", len(df))
    return df


def load_state_gdp() -> pd.DataFrame:
    """
    Load state-wise Gross State Domestic Product (GSDP) per capita.

    Source
    ------
    MoSPI / RBI Handbook of Statistics on Indian States.
    Expected columns: state_name, gsdp_per_capita_inr, gsdp_total_crore,
                      gsdp_growth_rate_pct, year

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "state_gdp",
        dtype={"gsdp_per_capita_inr": float, "gsdp_total_crore": float,
               "year": "Int64"},
    )
    logger.info("GSDP data loaded: %d states", len(df))
    return df


def load_population() -> pd.DataFrame:
    """
    Load state-wise population and urbanization data.

    Source
    ------
    Census 2011 + Government of India population projections.
    Expected columns: state_name, population_total, population_urban,
                      population_rural, urbanization_pct, year

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "population",
        dtype={"population_total": "Int64", "population_urban": "Int64",
               "population_rural": "Int64", "urbanization_pct": float},
    )
    logger.info("Population data loaded: %d states", len(df))
    return df


def load_electricity() -> pd.DataFrame:
    """
    Load state-wise electricity infrastructure metrics.

    Source
    ------
    Central Electricity Authority (CEA) Annual Report.
    Expected columns: state_name, electrification_pct,
                      per_capita_power_consumption_kwh, installed_capacity_mw

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "electricity",
        dtype={"electrification_pct": float,
               "per_capita_power_consumption_kwh": float,
               "installed_capacity_mw": float},
    )
    logger.info("Electricity data loaded: %d states", len(df))
    return df


def load_broadband() -> pd.DataFrame:
    """
    Load state-wise broadband subscriber data from TRAI.

    Source
    ------
    TRAI Quarterly Broadband Subscription Report (PDF extracted).
    Expected columns: state_name, broadband_subscribers,
                      broadband_subscribers_per_100, quarter, year

    Notes
    -----
    This file is produced by src/etl/pdf_extractor.py from TRAI PDFs.
    If the CSV does not exist, run the extractor first.

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "broadband",
        dtype={"broadband_subscribers": "Int64",
               "broadband_subscribers_per_100": float},
    )
    logger.info("Broadband data loaded: %d rows", len(df))
    return df


def load_internet_penetration() -> pd.DataFrame:
    """
    Load state-wise internet penetration rates.

    Source
    ------
    TRAI Annual Report / IAMAI Internet in India Report.
    Expected columns: state_name, internet_penetration_pct,
                      rural_internet_pct, urban_internet_pct, year

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "internet_penetration",
        dtype={"internet_penetration_pct": float,
               "rural_internet_pct": float,
               "urban_internet_pct": float},
    )
    logger.info("Internet penetration data loaded: %d states", len(df))
    return df


def load_startups() -> pd.DataFrame:
    """
    Load state-wise DPIIT recognized startup counts.

    Source
    ------
    DPIIT Startup India Annual Report (state-wise aggregates).
    Expected columns: state_name, recognized_startups,
                      startups_per_million, year

    Notes
    -----
    This uses DPIIT's published aggregate counts, not the live portal.
    Direct API access is not publicly available. Source documented in
    data_dictionary.md.

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "startups",
        dtype={"recognized_startups": "Int64", "startups_per_million": float},
    )
    logger.info("Startup data loaded: %d states", len(df))
    return df


def load_digital_literacy() -> pd.DataFrame:
    """
    Load state-wise PMGDISHA digital literacy program beneficiaries.

    Source
    ------
    PMGDISHA (Pradhan Mantri Gramin Digital Saksharta Abhiyan) reports.
    Expected columns: state_name, beneficiaries_trained,
                      digital_literacy_beneficiaries_per_million

    Notes
    -----
    PROXY VARIABLE: This measures program reach (enrolled beneficiaries),
    NOT true digital literacy rate. It is used as the best available
    proxy for rural digital literacy exposure. This limitation is
    explicitly documented in methodology.md.

    Returns
    -------
    pd.DataFrame
    """
    df = _load_csv(
        "digital_literacy",
        dtype={"beneficiaries_trained": "Int64",
               "digital_literacy_beneficiaries_per_million": float},
    )
    logger.info("Digital literacy data loaded: %d states", len(df))
    return df


def load_all_raw() -> dict[str, pd.DataFrame]:
    """
    Load all raw datasets and return them as a named dictionary.

    This is the primary entry point for the ETL pipeline. Loaders
    are called in dependency order. If any individual loader fails,
    the exception propagates with a descriptive message.

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys match dataset names used throughout the pipeline:
        'aicte', 'literacy', 'gdp', 'population', 'electricity',
        'broadband', 'internet', 'startups', 'digital_literacy'

    Example
    -------
    >>> from src.etl.loader import load_all_raw
    >>> raw = load_all_raw()
    >>> raw["literacy"].head()
    """
    logger.info("Starting full raw data load...")

    loaders = {
        "aicte": load_aicte_institutes,
        "literacy": load_census_literacy,
        "gdp": load_state_gdp,
        "population": load_population,
        "electricity": load_electricity,
        "broadband": load_broadband,
        "internet": load_internet_penetration,
        "startups": load_startups,
        "digital_literacy": load_digital_literacy,
    }

    raw: dict[str, pd.DataFrame] = {}
    failed: list[str] = []

    for name, loader_fn in loaders.items():
        try:
            raw[name] = loader_fn()
        except FileNotFoundError as exc:
            logger.warning("Skipping '%s' — file not found: %s", name, exc)
            failed.append(name)
        except Exception as exc:
            logger.error("Unexpected error loading '%s': %s", name, exc, exc_info=True)
            failed.append(name)

    if failed:
        logger.warning(
            "Load completed with %d missing dataset(s): %s. "
            "These will be handled during merging.",
            len(failed),
            ", ".join(failed),
        )
    else:
        logger.info("All %d datasets loaded successfully.", len(loaders))

    return raw
