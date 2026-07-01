"""
Data Cleaner
============
Standardizes, validates, and imputes missing values across all
raw DataFrames produced by loader.py.

This module enforces three guarantees on every cleaned DataFrame:
  1. The 'state_name' column uses canonical Census 2011 names
  2. Numeric columns are within plausible domain ranges
  3. Missing values are imputed and flagged with boolean columns

Design Decisions
----------------
State name standardization is driven by state_name_mapping in
settings.yaml — NOT hardcoded here. Adding a new spelling variant
requires editing only the YAML file.

Missing value strategy: regional median with national median fallback.
Imputed rows are flagged (e.g., 'literacy_rate_pct_imputed': True)
so downstream analyses can distinguish real from estimated values.

Public API
----------
standardize_state_names(df)         -> pd.DataFrame
validate_ranges(df, column_ranges)  -> pd.DataFrame  [logs warnings]
impute_missing(df, strategy)        -> pd.DataFrame
clean_dataset(df, column_ranges)    -> pd.DataFrame  [full pipeline]
clean_all(raw_dict)                 -> dict[str, pd.DataFrame]
"""

from typing import Optional

import numpy as np
import pandas as pd

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)

# ── Domain Validation Ranges ──────────────────────────────────────────────────
# These are sanity-check bounds. Values outside these ranges are
# logged as warnings and clamped. They do NOT represent expected
# data distributions — they catch data entry errors and format issues.

COLUMN_RANGES: dict[str, tuple[float, float]] = {
    "literacy_rate_pct": (0.0, 100.0),
    "male_literacy_pct": (0.0, 100.0),
    "female_literacy_pct": (0.0, 100.0),
    "internet_penetration_pct": (0.0, 100.0),
    "rural_internet_pct": (0.0, 100.0),
    "urban_internet_pct": (0.0, 100.0),
    "broadband_subscribers_per_100": (0.0, 200.0),
    "electrification_pct": (0.0, 100.0),
    "urbanization_pct": (0.0, 100.0),
    "gsdp_per_capita_inr": (1_000.0, 50_00_000.0),
    "per_capita_power_consumption_kwh": (0.0, 10_000.0),
    "startups_per_million": (0.0, 10_000.0),
}


# ── State Name Standardization ────────────────────────────────────────────────

def standardize_state_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map all state name variants to the canonical Census 2011 name.

    Uses state_name_mapping from settings.yaml. Unknown names are
    preserved as-is and logged as warnings for manual review.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a 'state_name' column.

    Returns
    -------
    pd.DataFrame
        Same shape as input with 'state_name' standardized.

    Raises
    ------
    KeyError
        If 'state_name' column is not present.
    """
    if "state_name" not in df.columns:
        raise KeyError(
            f"Expected 'state_name' column. Found: {list(df.columns)}"
        )

    cfg = get_config()
    mapping: dict[str, str] = cfg["state_name_mapping"]

    original_names = df["state_name"].copy()
    df = df.copy()
    df["state_name"] = df["state_name"].str.strip()
    df["state_name"] = df["state_name"].replace(mapping)

    # Log any names that weren't in the mapping (may need to be added)
    known_canonical = set(mapping.values())
    known_variants = set(mapping.keys())
    all_known = known_canonical | known_variants

    unmapped = set(df["state_name"].unique()) - known_canonical
    if unmapped:
        logger.warning(
            "Unrecognized state names (not in mapping or canonical list): %s\n"
            "If these are valid states, add them to state_name_mapping in settings.yaml.",
            sorted(unmapped),
        )

    changed = (original_names != df["state_name"]).sum()
    logger.debug("Standardized %d state name(s)", changed)

    return df


# ── Range Validation ──────────────────────────────────────────────────────────

def validate_ranges(
    df: pd.DataFrame,
    column_ranges: Optional[dict[str, tuple[float, float]]] = None,
) -> pd.DataFrame:
    """
    Validate numeric columns are within plausible domain ranges.

    Out-of-range values are clamped to the boundary and logged as
    warnings. This catches unit errors (e.g., subscribers in thousands
    when we expect absolute counts) before they propagate.

    Parameters
    ----------
    df : pd.DataFrame
    column_ranges : dict, optional
        Mapping of column_name -> (min_val, max_val).
        Defaults to the module-level COLUMN_RANGES constant.

    Returns
    -------
    pd.DataFrame
        Same shape as input with out-of-range values clamped.
    """
    if column_ranges is None:
        column_ranges = COLUMN_RANGES

    df = df.copy()

    for col, (min_val, max_val) in column_ranges.items():
        if col not in df.columns:
            continue

        out_of_range_mask = (
            df[col].notna() & ((df[col] < min_val) | (df[col] > max_val))
        )

        if out_of_range_mask.any():
            offending = df.loc[out_of_range_mask, ["state_name", col]]
            logger.warning(
                "Column '%s' has %d value(s) outside [%s, %s]:\n%s",
                col, out_of_range_mask.sum(), min_val, max_val,
                offending.to_string(index=False),
            )
            df[col] = df[col].clip(lower=min_val, upper=max_val)
            logger.debug("Clamped '%s' to [%s, %s]", col, min_val, max_val)

    return df


# ── Missing Value Imputation ──────────────────────────────────────────────────

def _build_region_map() -> dict[str, str]:
    """
    Build a state -> region mapping from settings.yaml.

    Returns
    -------
    dict[str, str]
        Maps canonical state name to region name.
    """
    cfg = get_config()
    region_map: dict[str, str] = {}
    for region, states in cfg["regions"].items():
        for state in states:
            region_map[state] = region
    return region_map


def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Impute missing numeric values using regional median with
    national median fallback. Flags every imputed cell.

    Strategy (from settings.yaml → missing_values):
    1. Assign each state to its geographic region
    2. Compute regional median for each numeric column
    3. Impute missing values with the regional median
    4. If regional median is also NaN (< 2 non-null values in region),
       fall back to national median
    5. Mark imputed rows with a boolean flag column: {col}_imputed

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'state_name' column.

    Returns
    -------
    pd.DataFrame
        Imputed DataFrame with boolean flag columns appended.
    """
    cfg = get_config()["missing_values"]
    max_missing_pct = cfg["max_missing_pct"]
    flag_imputed = cfg["flag_imputed"]

    df = df.copy()
    region_map = _build_region_map()
    df["_region"] = df["state_name"].map(region_map)

    unmapped_states = df.loc[df["_region"].isna(), "state_name"].unique()
    if len(unmapped_states) > 0:
        logger.warning(
            "States not assigned to any region (using national median fallback): %s",
            sorted(unmapped_states),
        )

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Exclude internal helper columns
    numeric_cols = [c for c in numeric_cols if not c.startswith("_")]

    dropped_cols: list[str] = []

    for col in numeric_cols:
        missing_pct = df[col].isna().mean()

        # Drop feature if too many values are missing
        if missing_pct > max_missing_pct:
            logger.warning(
                "Dropping column '%s': %.0f%% missing (threshold: %.0f%%)",
                col, missing_pct * 100, max_missing_pct * 100,
            )
            dropped_cols.append(col)
            continue

        if missing_pct == 0:
            continue

        missing_mask = df[col].isna()
        n_missing = missing_mask.sum()

        # Regional medians
        regional_medians = df.groupby("_region")[col].median()

        # National median as fallback
        national_median = df[col].median()

        imputed_count = 0

        for idx in df[missing_mask].index:
            region = df.at[idx, "_region"]
            regional_val = regional_medians.get(region, np.nan)

            if pd.notna(regional_val):
                df.at[idx, col] = regional_val
            else:
                df.at[idx, col] = national_median
                logger.debug(
                    "Used national median for %s / %s (region '%s' had insufficient data)",
                    df.at[idx, "state_name"], col, region,
                )
            imputed_count += 1

        if flag_imputed and n_missing > 0:
            flag_col = f"{col}_imputed"
            df[flag_col] = False
            df.loc[missing_mask, flag_col] = True

        logger.info(
            "Imputed %d missing value(s) in '%s' using regional/national median",
            imputed_count, col,
        )

    # Drop flagged columns
    if dropped_cols:
        df = df.drop(columns=dropped_cols)

    # Remove the helper region column
    df = df.drop(columns=["_region"])

    return df


# ── Full Clean Pipeline ───────────────────────────────────────────────────────

def clean_dataset(
    df: pd.DataFrame,
    dataset_name: str = "unknown",
    column_ranges: Optional[dict[str, tuple[float, float]]] = None,
) -> pd.DataFrame:
    """
    Run the full cleaning pipeline on a single DataFrame.

    Steps
    -----
    1. Standardize state names (YAML mapping)
    2. Validate and clamp out-of-range values
    3. Impute missing values with regional/national median

    Parameters
    ----------
    df : pd.DataFrame
    dataset_name : str
        Used in log messages for traceability.
    column_ranges : dict, optional
        Custom range overrides. Defaults to module-level COLUMN_RANGES.

    Returns
    -------
    pd.DataFrame
        Fully cleaned DataFrame.
    """
    logger.info("Cleaning dataset: %s (%d rows)", dataset_name, len(df))

    df = standardize_state_names(df)
    df = validate_ranges(df, column_ranges)
    df = impute_missing(df)

    logger.info("Cleaned dataset: %s → %d rows, %d columns", dataset_name, len(df), len(df.columns))
    return df


def clean_all(raw_dict: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    Apply the full cleaning pipeline to every dataset in the raw dict.

    Parameters
    ----------
    raw_dict : dict[str, pd.DataFrame]
        Output of loader.load_all_raw().

    Returns
    -------
    dict[str, pd.DataFrame]
        Same keys as input, with cleaned DataFrames as values.
    """
    logger.info("Starting cleaning for %d dataset(s)...", len(raw_dict))

    cleaned: dict[str, pd.DataFrame] = {}

    for name, df in raw_dict.items():
        try:
            cleaned[name] = clean_dataset(df, dataset_name=name)
        except Exception as exc:
            logger.error(
                "Failed to clean dataset '%s': %s", name, exc, exc_info=True
            )
            raise

    logger.info("All datasets cleaned successfully.")
    return cleaned
