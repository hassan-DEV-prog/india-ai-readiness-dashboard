"""
Feature Normalizer
==================
Applies Min-Max normalization to raw pillar features, converting
all metrics to a common [0, 1] scale before index construction.

Why Min-Max over Z-score?
-------------------------
Z-score normalization centers data around 0 and has no fixed upper
bound, which makes it difficult to interpret a composite score.
Min-Max guarantees [0, 1] output, where 0 = worst state on that
metric, 1 = best state. This is the standard used by UNDP HDI,
World Bank Doing Business Index, and the OECD composite indicator
handbook. The tradeoff is sensitivity to outliers, which we address
with optional pre-clipping.

Public API
----------
normalize_feature(series, clip_outliers)  -> pd.Series
normalize_pillar_features(df)             -> pd.DataFrame
compute_pillar_scores(df)                 -> pd.DataFrame
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)


# ── Single Feature Normalization ──────────────────────────────────────────────

def normalize_feature(
    series: pd.Series,
    clip_outliers: bool = True,
    outlier_std_threshold: float = 3.0,
) -> pd.Series:
    """
    Apply Min-Max normalization to a single feature Series.

    Parameters
    ----------
    series : pd.Series
        Raw numeric values for one feature across all states.
    clip_outliers : bool
        If True, values beyond `outlier_std_threshold` standard
        deviations from the mean are clipped before normalization.
        This prevents a single extreme outlier from compressing
        all other states toward zero.
    outlier_std_threshold : float
        Number of standard deviations used as the clipping boundary.
        Default 3.0 (retains 99.7% of a normal distribution).

    Returns
    -------
    pd.Series
        Normalized values in [0, 1]. Name preserved from input.
        NaN values remain NaN (not imputed here).

    Examples
    --------
    >>> s = pd.Series([10, 20, 30, 40, 50], name="internet_pct")
    >>> normalize_feature(s)
    0    0.00
    1    0.25
    2    0.50
    3    0.75
    4    1.00
    Name: internet_pct, dtype: float64
    """
    result = series.copy().astype(float)

    if clip_outliers and result.notna().sum() > 2:
        mean = result.mean()
        std = result.std()
        lower = mean - outlier_std_threshold * std
        upper = mean + outlier_std_threshold * std
        clipped = result.clip(lower=lower, upper=upper)

        n_clipped = (result != clipped).sum()
        if n_clipped > 0:
            logger.debug(
                "Feature '%s': clipped %d outlier(s) to [%.2f, %.2f]",
                series.name, n_clipped, lower, upper,
            )
        result = clipped

    min_val = result.min()
    max_val = result.max()

    if max_val == min_val:
        # All states have the same value — no discrimination possible
        # Return 0.5 (midpoint) rather than 0 or NaN
        logger.warning(
            "Feature '%s' has zero variance (all states identical: %.4f). "
            "Assigning 0.5 to all states.",
            series.name, min_val,
        )
        return pd.Series(
            np.where(result.notna(), 0.5, np.nan),
            index=result.index,
            name=series.name,
        )

    normalized = (result - min_val) / (max_val - min_val)
    return normalized.rename(series.name)


# ── Pillar-Level Normalization ────────────────────────────────────────────────

def normalize_pillar_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize all pillar features defined in settings.yaml.

    Reads the pillar → feature mapping from config and normalizes
    each feature independently. Returns a DataFrame with the same
    index as input but with all pillar features replaced by their
    [0, 1] normalized equivalents.

    Parameters
    ----------
    df : pd.DataFrame
        Master dataset (states_merged.csv). Must contain 'state_name'.

    Returns
    -------
    pd.DataFrame
        DataFrame with normalized pillar feature columns. Non-pillar
        columns (state_name, region, population, etc.) are preserved
        unchanged.
    """
    cfg = get_config()
    norm_cfg = cfg["normalization"]
    clip = norm_cfg.get("clip_outliers", True)
    threshold = norm_cfg.get("outlier_std_threshold", 3.0)
    pillars = cfg["pillars"]

    result = df.copy()

    all_pillar_features: list[str] = []
    for pillar_name, pillar_cfg in pillars.items():
        features = pillar_cfg["features"]
        all_pillar_features.extend(features)

        for feature in features:
            if feature not in df.columns:
                logger.warning(
                    "Pillar '%s': feature '%s' not found in dataset — skipping",
                    pillar_name, feature,
                )
                continue

            result[f"norm_{feature}"] = normalize_feature(
            df[feature],
            clip_outliers=clip,
            outlier_std_threshold=threshold,
        )
            # result[feature] = normalize_feature(
            #     df[feature],
            #     clip_outliers=clip,
            #     outlier_std_threshold=threshold,
            # )
            logger.debug(
                "Normalized [%-25s] %-45s range: [%.3f, %.3f]",
                pillar_name, feature,
                result[feature].min(), result[feature].max(),
            )

    logger.info(
        "Normalized %d pillar features across %d pillars",
        len(all_pillar_features), len(pillars),
    )

    return result


# ── Pillar Score Computation ──────────────────────────────────────────────────

def compute_pillar_scores(normalized_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-state pillar scores as the mean of normalized features.

    Each pillar score is the unweighted average of its constituent
    normalized features. The weighting across pillars happens in
    index_builder.py — this function only aggregates within pillars.

    Parameters
    ----------
    normalized_df : pd.DataFrame
        Output of normalize_pillar_features().

    Returns
    -------
    pd.DataFrame
        Original DataFrame with pillar score columns appended.
        New columns follow the naming convention: score_{pillar_name}
        e.g., score_internet, score_education, score_infrastructure

    Notes
    -----
    If a pillar has any feature missing for a state, that state's
    pillar score is the mean of available features only (not NaN).
    This is more robust than requiring all features to be present.
    """
    cfg = get_config()
    pillars = cfg["pillars"]

    result = normalized_df.copy()

    for pillar_name, pillar_cfg in pillars.items():
        features = pillar_cfg["features"]

        # Only use features that actually exist in the DataFrame
        available_features = [f"norm_{f}" for f in features if f"norm_{f}" in result.columns]
        missing_features = set(features) - {f.replace("norm_", "") for f in available_features}

        if missing_features:
            logger.warning(
                "Pillar '%s': %d feature(s) unavailable for scoring: %s",
                pillar_name, len(missing_features), sorted(missing_features),
            )

        if not available_features:
            logger.error(
                "Pillar '%s' has NO available features — pillar score will be NaN",
                pillar_name,
            )
            result[f"score_{pillar_name}"] = np.nan
            continue

        # Row-wise mean across available features, skipping NaN
        pillar_scores = result[available_features].mean(axis=1, skipna=True)
        result[f"score_{pillar_name}"] = pillar_scores

        logger.info(
            "Pillar %-20s | features: %d | score range: [%.3f, %.3f]",
            f"'{pillar_name}'",
            len(available_features),
            pillar_scores.min(),
            pillar_scores.max(),
        )

    return result
