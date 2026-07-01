"""
Correlation Analysis
====================
Computes Pearson and Spearman correlation matrices across pillar
scores and key features. Generates structured insight statements
from significant correlations for use on the dashboard.

Why both Pearson AND Spearman?
-------------------------------
Pearson measures LINEAR correlation. If two pillars are related
but non-linearly (e.g., GDP and startups follow a power law),
Pearson will understate the relationship. Spearman measures
RANK correlation and catches monotonic relationships regardless
of their shape. We report both and flag discrepancies.

Why avoid using raw features for correlation?
----------------------------------------------
Correlating 15 raw features produces a 15x15 matrix that is
visually cluttered and statistically overloaded. Correlating
5 pillar scores produces a clean 5x5 matrix that tells a cleaner
story on the dashboard.

Public API
----------
compute_correlation_matrix(df, method)      -> pd.DataFrame
find_significant_correlations(corr_matrix)  -> pd.DataFrame
generate_correlation_insights(df)           -> list[str]
run_correlation_analysis(index_df)          -> dict
"""

import pandas as pd
from scipy import stats

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)

# Threshold above which a correlation is considered noteworthy
_STRONG_THRESHOLD = 0.70
_MODERATE_THRESHOLD = 0.50


# ── Correlation Matrix ────────────────────────────────────────────────────────

def compute_correlation_matrix(
    df: pd.DataFrame,
    method: str = "spearman",
) -> pd.DataFrame:
    """
    Compute a correlation matrix across pillar score columns.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain score_{pillar} columns.
    method : str
        'pearson' or 'spearman'. Default: spearman.

    Returns
    -------
    pd.DataFrame
        Square correlation matrix with pillar labels as index/columns.
    """
    cfg = get_config()
    pillar_cols = {
        f"score_{p}": cfg["pillars"][p]["label"]
        for p in cfg["pillars"]
        if f"score_{p}" in df.columns
    }

    if not pillar_cols:
        raise ValueError("No pillar score columns found in DataFrame.")

    corr_df = df[list(pillar_cols.keys())].rename(columns=pillar_cols)
    matrix = corr_df.corr(method=method).round(3)

    logger.info(
        "Computed %s correlation matrix (%dx%d)",
        method.capitalize(), len(matrix), len(matrix.columns),
    )
    return matrix


# ── Significant Correlations ──────────────────────────────────────────────────

def find_significant_correlations(
    corr_matrix: pd.DataFrame,
    threshold: float = _MODERATE_THRESHOLD,
) -> pd.DataFrame:
    """
    Extract all unique pillar pairs with |correlation| >= threshold.

    Parameters
    ----------
    corr_matrix : pd.DataFrame
        Output of compute_correlation_matrix().
    threshold : float
        Minimum absolute correlation to report.

    Returns
    -------
    pd.DataFrame
        Columns: pillar_a, pillar_b, correlation, strength
        Sorted by absolute correlation descending.
    """
    rows: list[dict] = []
    cols = corr_matrix.columns.tolist()

    for i, a in enumerate(cols):
        for b in cols[i + 1:]:        # upper triangle only — avoid duplicates
            r = corr_matrix.loc[a, b]
            if abs(r) >= threshold:
                rows.append({
                    "pillar_a": a,
                    "pillar_b": b,
                    "correlation": r,
                    "strength": (
                        "Strong" if abs(r) >= _STRONG_THRESHOLD else "Moderate"
                    ),
                    "direction": "Positive" if r > 0 else "Negative",
                })

    result = pd.DataFrame(rows).sort_values(
        "correlation", key=abs, ascending=False
    ).reset_index(drop=True)

    logger.info(
        "Found %d significant correlations (|r| >= %.2f)",
        len(result), threshold,
    )
    return result


# ── Statistical Significance Testing ─────────────────────────────────────────

def test_correlation_significance(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    alpha: float = 0.05,
) -> dict:
    """
    Test whether a Pearson correlation is statistically significant.

    With only 36 states, we need r > ~0.33 for significance at p<0.05.
    This is worth checking because moderate-looking correlations may
    not be statistically meaningful with small N.

    Parameters
    ----------
    df : pd.DataFrame
    col_a, col_b : str
        Column names for the two variables.
    alpha : float
        Significance level. Default 0.05.

    Returns
    -------
    dict
        Keys: r, p_value, significant, n
    """
    clean = df[[col_a, col_b]].dropna()
    r, p_value = stats.pearsonr(clean[col_a], clean[col_b])

    return {
        "r": round(r, 4),
        "p_value": round(p_value, 4),
        "significant": p_value < alpha,
        "n": len(clean),
        "alpha": alpha,
    }


# ── Insight Generation ────────────────────────────────────────────────────────

def generate_correlation_insights(
    df: pd.DataFrame,
    spearman_matrix: pd.DataFrame,
    pearson_matrix: pd.DataFrame,
) -> list[str]:
    """
    Generate plain-English analytical statements from correlations.

    This is what separates the dashboard from a data dump. Each
    statement is a testable hypothesis that the user can explore.

    Parameters
    ----------
    df : pd.DataFrame
        Index DataFrame with pillar scores.
    spearman_matrix : pd.DataFrame
        Spearman correlation matrix.
    pearson_matrix : pd.DataFrame
        Pearson correlation matrix.

    Returns
    -------
    list[str]
        Ordered list of insight strings, strongest first.
    """
    cfg = get_config()
    insights: list[str] = []

    sig_corrs = find_significant_correlations(spearman_matrix, threshold=0.50)

    for _, row in sig_corrs.iterrows():
        a, b = row["pillar_a"], row["pillar_b"]
        r = row["correlation"]
        strength = row["strength"]
        direction = row["direction"]

        if direction == "Positive" and abs(r) >= _STRONG_THRESHOLD:
            insights.append(
                f"Strong co-movement: States that lead on **{a}** "
                f"also tend to lead on **{b}** (ρ = {r:.2f}). "
                f"Investing in one likely accelerates the other."
            )
        elif direction == "Positive" and abs(r) >= _MODERATE_THRESHOLD:
            insights.append(
                f"Moderate positive link between **{a}** and **{b}** (ρ = {r:.2f}). "
                f"These pillars reinforce each other but have independent variation."
            )
        elif direction == "Negative":
            insights.append(
                f"Unexpected negative relationship: **{a}** and **{b}** (ρ = {r:.2f}). "
                f"States strong on one tend to lag on the other — worth investigating."
            )

    # Check for Pearson vs Spearman divergence (signals non-linearity)
    for i, col_a in enumerate(spearman_matrix.columns):
        for col_b in spearman_matrix.columns[i+1:]:
            spear_r = spearman_matrix.loc[col_a, col_b]
            pear_r = pearson_matrix.loc[col_a, col_b]
            delta = abs(spear_r - pear_r)
            if delta > 0.20:
                insights.append(
                    f"Non-linear relationship detected between **{col_a}** and "
                    f"**{col_b}**: Spearman ρ = {spear_r:.2f} vs Pearson r = {pear_r:.2f}. "
                    f"The relationship is monotonic but not linear."
                )

    # Identify the pillar most correlated with overall AI score
    score_col = "ai_readiness_score"
    if score_col in df.columns:
        pillar_score_cols = {
            f"score_{p}": cfg["pillars"][p]["label"]
            for p in cfg["pillars"]
            if f"score_{p}" in df.columns
        }
        correlations_with_score = {
            label: df[col].corr(df[score_col], method="spearman")
            for col, label in pillar_score_cols.items()
        }
        top_pillar = max(correlations_with_score, key=lambda k: abs(correlations_with_score[k]))
        top_r = correlations_with_score[top_pillar]
        insights.append(
            f"**{top_pillar}** is the single strongest predictor of overall "
            f"AI Readiness Score (ρ = {top_r:.2f}). States seeking to improve "
            f"their ranking should prioritize this pillar."
        )

    logger.info("Generated %d correlation insights", len(insights))
    return insights


# ── Pipeline Entry Point ──────────────────────────────────────────────────────

def run_correlation_analysis(index_df: pd.DataFrame) -> dict:
    """
    Full correlation analysis pipeline.

    Parameters
    ----------
    index_df : pd.DataFrame
        Output of clustering pipeline (with pillar scores).

    Returns
    -------
    dict with keys:
        spearman_matrix  : pd.DataFrame
        pearson_matrix   : pd.DataFrame
        significant_pairs: pd.DataFrame
        insights         : list[str]
    """
    logger.info("Running correlation analysis...")

    spearman = compute_correlation_matrix(index_df, method="spearman")
    pearson = compute_correlation_matrix(index_df, method="pearson")
    sig_pairs = find_significant_correlations(spearman)
    insights = generate_correlation_insights(index_df, spearman, pearson)

    for insight in insights:
        # Strip markdown bold markers for log readability
        clean = insight.replace("**", "")
        logger.info("INSIGHT: %s", clean)

    return {
        "spearman_matrix": spearman,
        "pearson_matrix": pearson,
        "significant_pairs": sig_pairs,
        "insights": insights,
    }
