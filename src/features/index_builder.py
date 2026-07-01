"""
AI Readiness Index Builder
==========================
Computes the composite AI Readiness Score using entropy weighting.
Also runs an equal-weighting sensitivity check to validate that
the rankings are robust to the choice of weighting method.

Mathematical Approach
---------------------
1. For each pillar j, compute entropy E_j across m states:
      p_ij  = P_ij / sum_i(P_ij)          [relative share]
      E_j   = -(1/ln(m)) * sum_i(p_ij * ln(p_ij))  [Shannon entropy]
      d_j   = 1 - E_j                     [divergence = discrimination power]
      w_j   = d_j / sum_j(d_j)            [normalized entropy weight]

2. Composite score:
      AI_Score_i = sum_j(w_j * P_ij) * 100   [scaled to 0-100]

3. Sensitivity check:
      AI_Score_equal_i = mean_j(P_ij) * 100

Reference: OECD (2008), "Handbook on Constructing Composite Indicators:
Methodology and User Guide", Chapter 6: Weighting and Aggregation.

Public API
----------
compute_entropy_weights(pillar_scores_df)  -> dict[str, float]
compute_equal_weights(pillars)             -> dict[str, float]
compute_composite_score(df, weights)       -> pd.Series
compute_rankings(df, score_col)            -> pd.DataFrame
run_sensitivity_analysis(df)               -> pd.DataFrame
build_index(master_df)                     -> pd.DataFrame
save_index(df)                             -> Path
"""

from pathlib import Path

import numpy as np
import pandas as pd

from config.config_loader import get_config, resolve_path
from src.features.normalizer import compute_pillar_scores, normalize_pillar_features
from src.logger import get_logger

logger = get_logger(__name__)

# Small epsilon to avoid log(0) in entropy calculation
_EPSILON = 1e-10


# ── Entropy Weight Computation ────────────────────────────────────────────────

def compute_entropy_weights(pillar_scores_df: pd.DataFrame) -> dict[str, float]:
    """
    Compute entropy-based weights for each pillar.

    A pillar that strongly discriminates between states (high variance)
    receives a higher weight than one where all states score similarly.

    Parameters
    ----------
    pillar_scores_df : pd.DataFrame
        Must contain columns named score_{pillar} for each pillar
        defined in settings.yaml.

    Returns
    -------
    dict[str, float]
        Mapping of pillar_name -> weight. Weights sum to 1.0.

    Notes
    -----
    Handles edge cases:
    - Zero pillar scores: replaced with epsilon before log computation
    - Identical pillar scores across all states: weight = 0 (no info)
    - Weights are renormalized after edge case handling
    """
    cfg = get_config()
    pillars = list(cfg["pillars"].keys())
    m = len(pillar_scores_df)  # number of states

    if m < 2:
        raise ValueError(
            f"Entropy weighting requires at least 2 states. Got {m}."
        )

    ln_m = np.log(m)
    divergences: dict[str, float] = {}

    logger.info("Computing entropy weights across %d pillars, %d states", len(pillars), m)

    for pillar in pillars:
        score_col = f"score_{pillar}"

        if score_col not in pillar_scores_df.columns:
            logger.warning(
                "Pillar score column '%s' not found — assigning zero weight",
                score_col,
            )
            divergences[pillar] = 0.0
            continue

        scores = pillar_scores_df[score_col].values.astype(float)

        # Replace NaN with 0 (missing = worst) for weight computation
        scores = np.where(np.isnan(scores), 0.0, scores)

        col_sum = scores.sum()

        if col_sum == 0:
            logger.warning(
                "Pillar '%s' has all-zero scores — assigning zero weight",
                pillar,
            )
            divergences[pillar] = 0.0
            continue

        # Step 1: Normalize to probability distribution
        p = scores / col_sum

        # Step 2: Clip to [epsilon, 1] to avoid log(0)
        p = np.clip(p, _EPSILON, 1.0)

        # Step 3: Shannon entropy (normalized by ln(m) to bound in [0,1])
        entropy = -(1.0 / ln_m) * np.sum(p * np.log(p))

        # Step 4: Divergence (discrimination power)
        divergence = 1.0 - entropy
        divergences[pillar] = max(divergence, 0.0)  # Numerical safety

        logger.debug(
            "Pillar %-20s | entropy: %.4f | divergence: %.4f",
            f"'{pillar}'", entropy, divergence,
        )

    # Step 5: Normalize divergences to weights summing to 1.0
    total_divergence = sum(divergences.values())

    if total_divergence == 0:
        logger.warning(
            "All pillars have zero divergence — falling back to equal weights"
        )
        equal_w = 1.0 / len(pillars)
        return {p: equal_w for p in pillars}

    weights = {
        pillar: div / total_divergence
        for pillar, div in divergences.items()
    }

    # Verification: weights must sum to 1.0
    weight_sum = sum(weights.values())
    assert abs(weight_sum - 1.0) < 1e-9, f"Weights sum to {weight_sum}, expected 1.0"

    logger.info("Entropy weights computed:")
    for pillar, w in sorted(weights.items(), key=lambda x: -x[1]):
        cfg_pillar = cfg["pillars"][pillar]
        logger.info("  %-20s %.4f (%.1f%%)", cfg_pillar["label"], w, w * 100)

    return weights


def compute_equal_weights(pillars: list[str]) -> dict[str, float]:
    """
    Compute equal weights (1/n) for each pillar.

    Used as the sensitivity check baseline. If rankings under equal
    weighting are similar to entropy weighting, the index is robust.

    Parameters
    ----------
    pillars : list[str]
        List of pillar names.

    Returns
    -------
    dict[str, float]
        Equal weight for each pillar. All values = 1/len(pillars).
    """
    n = len(pillars)
    w = 1.0 / n
    weights = {p: w for p in pillars}
    logger.info("Equal weights: %.4f per pillar (%d pillars)", w, n)
    return weights


# ── Composite Score Computation ───────────────────────────────────────────────

def compute_composite_score(
    pillar_scores_df: pd.DataFrame,
    weights: dict[str, float],
    scale: float = 100.0,
) -> pd.Series:
    """
    Compute the weighted composite AI Readiness Score.

    Score = sum_j(w_j * P_ij) * scale

    Parameters
    ----------
    pillar_scores_df : pd.DataFrame
        Must contain score_{pillar} columns.
    weights : dict[str, float]
        Pillar weights summing to 1.0.
    scale : float
        Multiplier for readability. Default 100 → scores in [0, 100].

    Returns
    -------
    pd.Series
        Composite score per state, in [0, scale].
    """
    composite = pd.Series(0.0, index=pillar_scores_df.index)

    for pillar, weight in weights.items():
        score_col = f"score_{pillar}"
        if score_col not in pillar_scores_df.columns:
            logger.warning("Score column '%s' missing — treated as 0", score_col)
            continue

        scores = pillar_scores_df[score_col].fillna(0.0)
        composite += weight * scores

    return (composite * scale).round(2)


# ── Ranking ───────────────────────────────────────────────────────────────────

def compute_rankings(df: pd.DataFrame, score_col: str) -> pd.DataFrame:
    """
    Add rank and percentile columns for a given score column.

    Parameters
    ----------
    df : pd.DataFrame
    score_col : str
        Column containing the composite score to rank.

    Returns
    -------
    pd.DataFrame
        With two new columns:
        - {score_col}_rank      : integer rank (1 = best)
        - {score_col}_percentile: percentile score (100 = best)
    """
    df = df.copy()
    df[f"{score_col}_rank"] = (
        df[score_col].rank(ascending=False, method="min").astype(int)
    )
    df[f"{score_col}_percentile"] = (
        df[score_col].rank(pct=True) * 100
    ).round(1)
    return df


# ── Sensitivity Analysis ──────────────────────────────────────────────────────

def run_sensitivity_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare entropy-weighted vs equal-weighted rankings.

    A high rank correlation between the two methods indicates the
    composite index is robust — i.e., it's not sensitive to the
    specific choice of weighting method.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain both ai_readiness_score and ai_readiness_score_equal.

    Returns
    -------
    pd.DataFrame
        Summary table with both ranks and rank differences, sorted
        by entropy rank.
    """
    required = ["state_name", "ai_readiness_score", "ai_readiness_score_equal"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in DataFrame")

    summary = df[["state_name", "ai_readiness_score", "ai_readiness_score_equal"]].copy()
    summary["rank_entropy"] = (
        summary["ai_readiness_score"].rank(ascending=False, method="min").astype(int)
    )
    summary["rank_equal"] = (
        summary["ai_readiness_score_equal"].rank(ascending=False, method="min").astype(int)
    )
    summary["rank_difference"] = (
        summary["rank_entropy"] - summary["rank_equal"]
    ).abs()

    # Spearman rank correlation between the two methods
    spearman_corr = summary["rank_entropy"].corr(
        summary["rank_equal"], method="spearman"
    )

    logger.info(
        "Sensitivity Analysis — Spearman rank correlation "
        "(entropy vs equal weights): %.4f",
        spearman_corr,
    )

    if spearman_corr >= 0.90:
        logger.info(
            "✓ HIGH robustness: Rankings are stable across weighting methods "
            "(correlation = %.4f)", spearman_corr
        )
    elif spearman_corr >= 0.75:
        logger.warning(
            "⚠ MODERATE robustness: Some rank shifts between methods "
            "(correlation = %.4f). Review divergent states.", spearman_corr
        )
    else:
        logger.warning(
            "✗ LOW robustness: Rankings change significantly with weighting method "
            "(correlation = %.4f). Investigate pillar definitions.", spearman_corr
        )

    summary["spearman_correlation"] = round(spearman_corr, 4)
    return summary.sort_values("rank_entropy").reset_index(drop=True)


# ── Full Index Build Pipeline ─────────────────────────────────────────────────

def build_index(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    Run the complete index construction pipeline.

    Steps
    -----
    1. Normalize all pillar features (Min-Max)
    2. Compute pillar scores (mean of normalized features per pillar)
    3. Compute entropy weights from pillar scores
    4. Compute AI Readiness Score (entropy-weighted)
    5. Compute AI Readiness Score (equal-weighted, sensitivity check)
    6. Add ranks and percentiles for both scoring methods
    7. Run sensitivity analysis and log Spearman correlation

    Parameters
    ----------
    master_df : pd.DataFrame
        Output of merger.run_merge_pipeline() (states_merged.csv).

    Returns
    -------
    pd.DataFrame
        Complete AI Readiness Index with all scores, ranks, and
        pillar breakdowns. Ready for dashboard consumption.
    """
    cfg = get_config()
    pillars = list(cfg["pillars"].keys())

    logger.info("=== Building AI Readiness Index ===")
    logger.info("States: %d | Pillars: %d", len(master_df), len(pillars))

    # Step 1: Normalize features
    logger.info("[1/6] Normalizing pillar features...")
    normalized_df = normalize_pillar_features(master_df)

    # Step 2: Compute pillar scores
    logger.info("[2/6] Computing pillar scores...")
    scored_df = compute_pillar_scores(normalized_df)

    # Step 3: Entropy weights
    logger.info("[3/6] Computing entropy weights...")
    entropy_weights = compute_entropy_weights(scored_df)

    # Step 4: Entropy-weighted composite score
    logger.info("[4/6] Computing entropy-weighted AI Readiness Score...")
    scored_df["ai_readiness_score"] = compute_composite_score(
        scored_df, entropy_weights
    )

    # Step 5: Equal-weighted score (sensitivity check)
    logger.info("[5/6] Computing equal-weighted score (sensitivity check)...")
    equal_weights = compute_equal_weights(pillars)
    scored_df["ai_readiness_score_equal"] = compute_composite_score(
        scored_df, equal_weights
    )

    # Step 6: Rankings
    logger.info("[6/6] Computing rankings...")
    scored_df = compute_rankings(scored_df, "ai_readiness_score")
    scored_df = compute_rankings(scored_df, "ai_readiness_score_equal")

    # Store weights in a serializable format (as columns for Power BI)
    for pillar, w in entropy_weights.items():
        scored_df[f"weight_{pillar}"] = round(w, 4)

    # Sensitivity analysis
    sensitivity = run_sensitivity_analysis(scored_df)
    spearman = sensitivity["spearman_correlation"].iloc[0]
    scored_df["sensitivity_spearman"] = spearman

    logger.info("=== Index Build Complete ===")
    logger.info(
        "Score range: [%.1f, %.1f]",
        scored_df["ai_readiness_score"].min(),
        scored_df["ai_readiness_score"].max(),
    )
    logger.info(
        "Top 5 states:\n%s",
        scored_df.nsmallest(5, "ai_readiness_score_rank")[
            ["state_name", "ai_readiness_score", "ai_readiness_score_rank"]
        ].to_string(index=False),
    )

    return scored_df


# ── Persistence ───────────────────────────────────────────────────────────────

def save_index(df: pd.DataFrame) -> Path:
    """
    Save the AI Readiness Index to data/processed/ai_readiness_index.csv.

    This is the primary file consumed by all 7 dashboard pages
    and the Power BI file.

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

    output_path = output_dir / "ai_readiness_index.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")

    logger.info(
        "AI Readiness Index saved: %s (%d states, %d columns, %.1f KB)",
        output_path,
        len(df),
        len(df.columns),
        output_path.stat().st_size / 1024,
    )

    return output_path
