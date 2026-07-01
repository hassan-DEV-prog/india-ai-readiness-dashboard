"""
Data Merger
===========
Joins all cleaned, standardized DataFrames into a single master
state-level dataset: states_merged.csv.

Design Decisions
----------------
- Left join on canonical state names: every state in the
  canonical list appears in the output, even if a dataset has
  no data for it (NaNs are handled by cleaner.py already)
- The canonical state list is derived from settings.yaml regions,
  ensuring we use the same authoritative list everywhere
- Per-capita normalization of absolute counts happens here,
  before feature engineering, because it requires the population
  dataset to be present
- Output is saved to data/processed/ — this is the single file
  that feeds BOTH the Streamlit dashboard and the Power BI file

Public API
----------
get_canonical_states()      -> list[str]
build_master_dataset(...)   -> pd.DataFrame
save_master_dataset(df)     -> Path
run_merge_pipeline()        -> pd.DataFrame  [entry point]
"""

from pathlib import Path

import pandas as pd

from config.config_loader import get_config, resolve_path
from src.logger import get_logger

logger = get_logger(__name__)


# ── Canonical State List ──────────────────────────────────────────────────────

def get_canonical_states() -> list[str]:
    """
    Return the authoritative list of Indian states and UTs.

    Derived from the 'regions' section of settings.yaml, which maps
    every region to its member states. This is the single source of
    truth for which states should appear in the output dataset.

    Returns
    -------
    list[str]
        Sorted list of canonical state/UT names.
    """
    cfg = get_config()
    states: list[str] = []
    for region_states in cfg["regions"].values():
        states.extend(region_states)
    return sorted(set(states))


# ── Per-Capita Normalization ──────────────────────────────────────────────────

def _compute_per_capita_metrics(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Derive per-million population metrics from absolute counts.

    This is done here (not in normalizer.py) because it is a domain
    transformation, not a statistical normalization. These derived
    columns are meaningful on their own (e.g., startups per million
    is comparable across states of different sizes).

    Columns derived
    ---------------
    - aicte_institutes_per_million  (from total_institutes + population)
    - engineering_seats_per_million (from engineering_seats + population)
    - startups_per_million          (from recognized_startups + population)
    - digital_literacy_beneficiaries_per_million (from beneficiaries_trained)

    Parameters
    ----------
    df : pd.DataFrame
        Merged DataFrame that already contains population_total.

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()
    pop = df["population_total"]

    per_million = pop / 1_000_000

    # Only compute if source columns exist
    derivations = {
        "aicte_institutes_per_million": "total_institutes",
        "engineering_seats_per_million": "engineering_seats",
        "startups_per_million": "recognized_startups",
        "digital_literacy_beneficiaries_per_million": "beneficiaries_trained",
    }

    for derived_col, source_col in derivations.items():
        if source_col in df.columns:
            # Avoid division by zero for UTs with tiny populations
            df[derived_col] = (df[source_col] / per_million).where(
                per_million > 0, other=0
            )
            logger.debug("Derived '%s' from '%s'", derived_col, source_col)
        else:
            logger.warning(
                "Cannot derive '%s': source column '%s' not found",
                derived_col, source_col,
            )

    return df


# ── Region Assignment ─────────────────────────────────────────────────────────

def _assign_regions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a 'region' column based on settings.yaml regional groupings.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'state_name' column.

    Returns
    -------
    pd.DataFrame
        With 'region' column added.
    """
    cfg = get_config()
    region_map: dict[str, str] = {}
    for region, states in cfg["regions"].items():
        for state in states:
            region_map[state] = region

    df = df.copy()
    df["region"] = df["state_name"].map(region_map).fillna("Unknown")

    unmapped = df.loc[df["region"] == "Unknown", "state_name"].tolist()
    if unmapped:
        logger.warning("States without region assignment: %s", unmapped)

    return df


# ── Master Dataset Builder ────────────────────────────────────────────────────

def build_master_dataset(
    cleaned: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Join all cleaned datasets into a single master state-level DataFrame.

    Join Strategy
    -------------
    Start with the canonical state list as the spine. Left-join each
    dataset on 'state_name'. This guarantees:
    - Every canonical state appears exactly once
    - Missing data from any single source does not drop states
    - Join failures are logged with row counts for debugging

    Parameters
    ----------
    cleaned : dict[str, pd.DataFrame]
        Output of cleaner.clean_all(). Keys expected:
        'aicte', 'literacy', 'gdp', 'population', 'electricity',
        'broadband', 'internet', 'startups', 'digital_literacy'

    Returns
    -------
    pd.DataFrame
        Master dataset with one row per state/UT.

    Raises
    ------
    ValueError
        If duplicate state names are found after joining.
    """
    canonical_states = get_canonical_states()
    logger.info(
        "Building master dataset for %d canonical states/UTs",
        len(canonical_states),
    )

    # Spine: one row per canonical state
    master = pd.DataFrame({"state_name": canonical_states})

    # Columns to retain from each dataset (avoids dragging in flag columns
    # that would clutter the master — they're available in individual files)
    join_specs: list[tuple[str, list[str]]] = [
        ("population", [
            "state_name", "population_total", "population_urban",
            "population_rural", "urbanization_pct",
        ]),
        ("literacy", [
            "state_name", "literacy_rate_pct", "male_literacy_pct",
            "female_literacy_pct", "rural_literacy_pct",
        ]),
        ("gdp", [
            "state_name", "gsdp_per_capita_inr", "gsdp_total_crore",
            "gsdp_growth_rate_pct",
        ]),
        ("electricity", [
            "state_name", "electrification_pct",
            "per_capita_power_consumption_kwh", "installed_capacity_mw",
        ]),
        ("internet", [
            "state_name", "internet_penetration_pct",
            "rural_internet_pct", "urban_internet_pct",
        ]),
        ("broadband", [
            "state_name", "broadband_subscribers",
            "broadband_subscribers_per_100",
        ]),
        ("aicte", [
            "state_name", "total_institutes", "total_seats",
            "engineering_seats",
        ]),
        ("startups", [
            "state_name", "recognized_startups",
        ]),
        ("digital_literacy", [
            "state_name", "beneficiaries_trained",
        ]),
    ]

    for dataset_name, columns in join_specs:
        if dataset_name not in cleaned:
            logger.warning(
                "Dataset '%s' not available — affected columns will be NaN",
                dataset_name,
            )
            continue

        df = cleaned[dataset_name]

        # Select only columns that exist in this specific dataset
        available_cols = [c for c in columns if c in df.columns]
        missing_cols = set(columns) - set(available_cols)
        if missing_cols:
            logger.warning(
                "Dataset '%s' missing expected columns: %s",
                dataset_name, sorted(missing_cols),
            )

        df_subset = df[available_cols].drop_duplicates(subset="state_name")

        pre_merge_count = len(master)
        master = master.merge(df_subset, on="state_name", how="left")
        post_merge_count = len(master)

        if post_merge_count != pre_merge_count:
            raise ValueError(
                f"Merge with '{dataset_name}' changed row count from "
                f"{pre_merge_count} to {post_merge_count}. "
                "Check for duplicate state names in the dataset."
            )

        joined = master["state_name"].isin(df["state_name"]).sum()
        logger.info(
            "Joined %-20s | %d/%d states matched",
            dataset_name, joined, len(master),
        )

    # ── Derived Metrics ───────────────────────────────────────
    master = _compute_per_capita_metrics(master)

    # ── Region Column ─────────────────────────────────────────
    master = _assign_regions(master)

    # ── Final Validation ──────────────────────────────────────
    if master["state_name"].duplicated().any():
        dupes = master[master["state_name"].duplicated()]["state_name"].tolist()
        raise ValueError(f"Duplicate states in master dataset: {dupes}")

    missing_summary = master.isna().sum()
    cols_with_missing = missing_summary[missing_summary > 0]
    if not cols_with_missing.empty:
        logger.warning(
            "Master dataset has remaining NaN values (review data sources):\n%s",
            cols_with_missing.to_string(),
        )

    logger.info(
        "Master dataset built: %d states × %d features",
        len(master), len(master.columns),
    )

    return master


# ── Persistence ───────────────────────────────────────────────────────────────

def save_master_dataset(df: pd.DataFrame) -> Path:
    """
    Save the master dataset to data/processed/states_merged.csv.

    This is the single file consumed by:
    - Streamlit dashboard (reads via pandas)
    - Power BI (connects via CSV connector)
    - Feature engineering modules

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    Path
        Absolute path of the saved file.
    """
    cfg = get_config()
    output_dir = resolve_path(cfg["paths"]["data_processed"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "states_merged.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")

    logger.info(
        "Master dataset saved: %s (%d rows, %d columns, %.1f KB)",
        output_path,
        len(df),
        len(df.columns),
        output_path.stat().st_size / 1024,
    )

    return output_path


# ── Pipeline Entry Point ──────────────────────────────────────────────────────

def run_merge_pipeline(
    cleaned: dict[str, pd.DataFrame],
    save: bool = True,
) -> pd.DataFrame:
    """
    Build the master dataset and optionally save it to disk.

    This is the primary entry point called by the top-level pipeline
    script and notebooks.

    Parameters
    ----------
    cleaned : dict[str, pd.DataFrame]
        Output of cleaner.clean_all().
    save : bool
        If True (default), persist to data/processed/states_merged.csv.

    Returns
    -------
    pd.DataFrame
        The master state-level dataset.
    """
    master = build_master_dataset(cleaned)

    if save:
        save_master_dataset(master)

    return master
