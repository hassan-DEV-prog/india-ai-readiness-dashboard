"""
Gap Analysis
============
Identifies, for each state, which pillars are underperforming
relative to the state's own average and relative to its cluster peers.

This module produces the consulting-style narrative output:
  "Karnataka ranks 9th overall. Its Innovation score (0.35) is
   significantly below its cluster average (0.52), suggesting that
   strong infrastructure and internet readiness have not yet
   translated into startup activity."

Two types of gap are detected
------------------------------
1. ABSOLUTE GAP: Pillar score vs national median for that pillar.
   "This state's internet score is in the bottom quartile nationally."

2. RELATIVE GAP: Pillar score vs state's own mean across pillars.
   "Internet is this state's weakest pillar relative to its strengths."

The relative gap is more actionable: it identifies the specific
bottleneck holding a well-performing state back.

Public API
----------
compute_pillar_gaps(df)                -> pd.DataFrame
classify_gap_severity(gap_value)       -> str
generate_state_narrative(state_row)    -> str
generate_all_narratives(gap_df)        -> pd.DataFrame
identify_opportunity_states(gap_df)    -> pd.DataFrame
run_gap_analysis(index_df)             -> dict
"""

import pandas as pd
import numpy as np

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)

# Gap severity thresholds (as fraction of full [0,1] pillar score range)
_GAP_SEVERE = 0.30      # > 30 points below state's own mean
_GAP_MODERATE = 0.15    # 15–30 points below
_GAP_MINOR = 0.05       # 5–15 points below


# ── Pillar Gap Computation ────────────────────────────────────────────────────

def compute_pillar_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute absolute and relative pillar gaps for every state.

    For each state i and pillar j:
      - absolute_gap_j  = national_median_j - score_j
                          (positive = below national median)
      - relative_gap_j  = state_mean_across_pillars - score_j
                          (positive = below this state's own average)
      - cluster_gap_j   = cluster_mean_j - score_j
                          (positive = below cluster peer average)

    Parameters
    ----------
    df : pd.DataFrame
        Must contain score_{pillar} and cluster_label columns.

    Returns
    -------
    pd.DataFrame
        Original df enriched with gap columns:
        abs_gap_{pillar}, rel_gap_{pillar}, cluster_gap_{pillar},
        weakest_pillar, weakest_pillar_score, state_pillar_mean
    """
    cfg = get_config()
    pillars = list(cfg["pillars"].keys())
    score_cols = [f"score_{p}" for p in pillars if f"score_{p}" in df.columns]
    pillar_labels = {
        f"score_{p}": cfg["pillars"][p]["label"]
        for p in pillars
        if f"score_{p}" in df.columns
    }

    df = df.copy()

    # ── National medians ─────────────────────────────────────
    national_medians = df[score_cols].median()

    # ── Cluster means ─────────────────────────────────────────
    if "cluster_label" in df.columns:
        cluster_means = df.groupby("cluster_label")[score_cols].mean()
    else:
        cluster_means = None
        logger.warning("cluster_label not found — cluster gap will not be computed")

    # ── State mean across pillars ──────────────────────────────
    df["state_pillar_mean"] = df[score_cols].mean(axis=1).round(4)

    # ── Compute gap columns ────────────────────────────────────
    for col in score_cols:
        # Absolute gap: how far below the national median
        df[f"abs_gap_{col}"] = (national_medians[col] - df[col]).round(4)

        # Relative gap: how far below this state's own average
        df[f"rel_gap_{col}"] = (df["state_pillar_mean"] - df[col]).round(4)

        # Cluster gap: how far below cluster peers
        if cluster_means is not None and "cluster_label" in df.columns:
            df[f"cluster_gap_{col}"] = df.apply(
                lambda row: (
                    cluster_means.loc[row["cluster_label"], col] - row[col]
                    if row["cluster_label"] in cluster_means.index
                    else np.nan
                ),
                axis=1,
            ).round(4)

    # ── Identify weakest pillar per state ─────────────────────
    # Weakest = highest relative gap (most below own average)
    rel_gap_cols = [f"rel_gap_{c}" for c in score_cols]
    available_rel = [c for c in rel_gap_cols if c in df.columns]

    if available_rel:
        weakest_col_idx = df[available_rel].idxmax(axis=1)
        # Map rel_gap_score_X → pillar label
        df["weakest_pillar"] = weakest_col_idx.map(
            lambda c: pillar_labels.get(
                c.replace("rel_gap_", ""), c
            ) if pd.notna(c) else "Unknown"
        )
        df["weakest_pillar_score"] = df.apply(
            lambda row: row[
                weakest_col_idx[row.name].replace("rel_gap_", "")
            ] if pd.notna(weakest_col_idx.get(row.name)) else np.nan,
            axis=1,
        ).round(4)

    # ── Identify strongest pillar per state ───────────────────
    strongest_col_idx = df[score_cols].idxmax(axis=1)
    df["strongest_pillar"] = strongest_col_idx.map(
        lambda c: pillar_labels.get(c, c)
    )
    df["strongest_pillar_score"] = df.apply(
        lambda row: row[strongest_col_idx[row.name]],
        axis=1,
    ).round(4)

    logger.info(
        "Gap analysis computed: %d states × %d pillars",
        len(df), len(score_cols),
    )

    return df


# ── Gap Severity Classification ───────────────────────────────────────────────

def classify_gap_severity(gap_value: float) -> str:
    """
    Classify a gap value into a severity category.

    Parameters
    ----------
    gap_value : float
        Relative or absolute gap (positive = underperforming).

    Returns
    -------
    str
        One of: 'Critical', 'Significant', 'Minor', 'On Par', 'Ahead'
    """
    if pd.isna(gap_value):
        return "Unknown"
    if gap_value > _GAP_SEVERE:
        return "Critical"
    elif gap_value > _GAP_MODERATE:
        return "Significant"
    elif gap_value > _GAP_MINOR:
        return "Minor"
    elif gap_value > -_GAP_MINOR:
        return "On Par"
    else:
        return "Ahead"


# ── Narrative Generation ──────────────────────────────────────────────────────

def generate_state_narrative(row: pd.Series) -> str:
    """
    Generate a one-paragraph consulting-style narrative for a state.

    This is the core output of the gap analysis module. Each narrative
    names the state's rank, strongest pillar, weakest pillar, and
    the specific strategic implication.

    Parameters
    ----------
    row : pd.Series
        A single row from the gap-enriched DataFrame.

    Returns
    -------
    str
        Plain-text narrative paragraph.
    """
    cfg = get_config()
    state = row.get("state_name", "This state")
    rank = row.get("ai_readiness_score_rank", "N/A")
    score = row.get("ai_readiness_score", 0)
    cluster = row.get("cluster_label", "Unknown")
    strongest = row.get("strongest_pillar", "Unknown")
    weakest = row.get("weakest_pillar", "Unknown")
    weakest_score = row.get("weakest_pillar_score", 0)
    state_mean = row.get("state_pillar_mean", 0)

    # Quantify the gap
    gap_magnitude = state_mean - weakest_score
    severity = classify_gap_severity(gap_magnitude)

    # Strategic implication by severity
    implications = {
        "Critical": (
            f"This is a structural barrier requiring immediate policy intervention. "
            f"Until {weakest} gaps are addressed, overall AI readiness gains will be limited."
        ),
        "Significant": (
            f"Targeted investment in {weakest} could unlock substantial AI readiness gains "
            f"given the state's existing strengths in {strongest}."
        ),
        "Minor": (
            f"A moderate improvement in {weakest} would likely move {state} "
            f"up 2–4 positions in the national ranking."
        ),
        "On Par": (
            f"{state} shows balanced development across all pillars. "
            f"Sustained progress across the board will maintain its competitive position."
        ),
        "Ahead": (
            f"{state} demonstrates consistent strength across pillars with no obvious bottlenecks."
        ),
    }

    implication = implications.get(severity, "")

    narrative = (
        f"{state} ranks #{rank} nationally with an AI Readiness Score of {score:.1f}/100, "
        f"placing it in the '{cluster}' tier. "
        f"Its strongest pillar is {strongest}, "
        f"while {weakest} (score: {weakest_score:.2f}) lags significantly behind "
        f"its own average across pillars ({state_mean:.2f}). "
        f"{implication}"
    )

    return narrative


def generate_all_narratives(gap_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply narrative generation to every state.

    Parameters
    ----------
    gap_df : pd.DataFrame
        Output of compute_pillar_gaps().

    Returns
    -------
    pd.DataFrame
        With 'state_narrative' column added.
    """
    gap_df = gap_df.copy()
    gap_df["state_narrative"] = gap_df.apply(
        generate_state_narrative, axis=1
    )
    logger.info("Generated narratives for %d states", len(gap_df))
    return gap_df


# ── Opportunity State Detection ───────────────────────────────────────────────

def identify_opportunity_states(gap_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify states with high potential but low current readiness.

    'Opportunity states' are defined as:
    - AI Readiness Score below the national median (current rank > 18)
    - BUT at least one pillar scoring in the top third nationally

    These are states where one strong dimension hasn't yet
    translated into overall AI readiness — often due to a single
    critical bottleneck. This is a high-value insight for policymakers.

    Parameters
    ----------
    gap_df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
        Subset of states classified as opportunities, with their
        strongest pillar and critical gap identified.
    """
    cfg = get_config()
    score_cols = [f"score_{p}" for p in cfg["pillars"] if f"score_{p}" in gap_df.columns]

    median_ai_score = gap_df["ai_readiness_score"].median()
    top_third_threshold = gap_df[score_cols].quantile(0.67)

    # Flag states below median AI score
    below_median = gap_df["ai_readiness_score"] < median_ai_score

    # Flag states with at least one pillar in top third
    has_strong_pillar = (gap_df[score_cols] >= top_third_threshold).any(axis=1)

    opportunity_mask = below_median & has_strong_pillar
    opportunity_states = gap_df[opportunity_mask].copy()
    opportunity_states["opportunity_type"] = "Latent Potential"

    logger.info(
        "Identified %d opportunity states (below-median AI score "
        "but with top-third strength in ≥1 pillar)",
        len(opportunity_states),
    )

    if not opportunity_states.empty:
        logger.info(
            "Opportunity states: %s",
            opportunity_states["state_name"].tolist(),
        )

    return opportunity_states[
        ["state_name", "ai_readiness_score", "ai_readiness_score_rank",
         "strongest_pillar", "weakest_pillar", "cluster_label",
         "opportunity_type", "state_narrative"]
    ].sort_values("ai_readiness_score", ascending=False)


# ── Pipeline Entry Point ──────────────────────────────────────────────────────

def run_gap_analysis(index_df: pd.DataFrame) -> dict:
    """
    Full gap analysis pipeline.

    Parameters
    ----------
    index_df : pd.DataFrame
        Output of clustering pipeline.

    Returns
    -------
    dict with keys:
        gap_df             : pd.DataFrame  (enriched with all gap columns)
        opportunity_states : pd.DataFrame  (latent potential states)
        narratives         : pd.Series     (one narrative per state)
    """
    logger.info("Running gap analysis...")

    gap_df = compute_pillar_gaps(index_df)
    gap_df = generate_all_narratives(gap_df)
    opportunity_states = identify_opportunity_states(gap_df)

    return {
        "gap_df": gap_df,
        "opportunity_states": opportunity_states,
        "narratives": gap_df.set_index("state_name")["state_narrative"],
    }
