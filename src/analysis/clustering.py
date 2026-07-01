"""
State Clustering
================
Segments Indian states into peer groups using K-Means clustering
on pillar scores. This enables peer comparison ("Kerala underperforms
its cluster peers on innovation") rather than only national ranking.

Why K-Means over Hierarchical Clustering?
------------------------------------------
- K-Means is interpretable: fixed number of clusters maps cleanly
  to dashboard categories (Leaders / Challengers / Emerging / Laggards)
- With only 36 states, K-Means is stable and fast
- The number of clusters (k=4) is set in settings.yaml and validated
  with the elbow method below
- Hierarchical clustering would require a dendrogram to interpret —
  not suitable for a dashboard audience

Why cluster on PILLAR SCORES, not raw features?
------------------------------------------------
Clustering on 15 raw features with different units would weight
high-magnitude features (GSDP in crores) over percentage features.
Pillar scores are already normalized to [0,1], making them
geometrically comparable without further scaling.

Public API
----------
run_elbow_analysis(df, k_range)      -> dict[int, float]
assign_clusters(df, n_clusters)      -> pd.DataFrame
label_clusters(df)                   -> pd.DataFrame
get_cluster_summary(df)              -> pd.DataFrame
run_clustering_pipeline(index_df)    -> pd.DataFrame
"""

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)


# ── Elbow Analysis ────────────────────────────────────────────────────────────

def run_elbow_analysis(
    df: pd.DataFrame,
    pillar_cols: list[str],
    k_range: range = range(2, 8),
) -> dict[int, float]:
    """
    Compute inertia and silhouette scores for k=2..7.

    Used to validate that k=4 (set in config) is a defensible choice.
    In a professional context, you present this plot in the methodology
    section to justify the cluster count.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain pillar score columns.
    pillar_cols : list[str]
        Pillar score column names to cluster on.
    k_range : range
        Range of k values to test.

    Returns
    -------
    dict[int, float]
        Mapping of k -> silhouette score. Higher = better separation.
    """
    cfg = get_config()
    random_state = cfg["clustering"]["random_state"]
    X = df[pillar_cols].fillna(0.0).values

    results: dict[int, float] = {}

    for k in k_range:
        if k >= len(df):
            break
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)
        results[k] = round(sil, 4)
        logger.debug("k=%d | silhouette=%.4f | inertia=%.2f", k, sil, km.inertia_)

    best_k = max(results, key=results.get)
    logger.info(
        "Elbow analysis complete. Best silhouette at k=%d (%.4f). "
        "Config uses k=%d.",
        best_k, results[best_k],
        cfg["clustering"]["n_clusters"],
    )

    return results


# ── Cluster Assignment ────────────────────────────────────────────────────────

def assign_clusters(
    df: pd.DataFrame,
    pillar_cols: list[str],
    n_clusters: Optional[int] = None,
) -> pd.DataFrame:
    """
    Run K-Means and assign each state to a cluster.

    Parameters
    ----------
    df : pd.DataFrame
    pillar_cols : list[str]
        Columns to cluster on (pillar scores).
    n_clusters : int, optional
        Number of clusters. Defaults to config value.

    Returns
    -------
    pd.DataFrame
        With 'cluster_id' column (0-indexed integers) added.
    """
    cfg = get_config()
    if n_clusters is None:
        n_clusters = cfg["clustering"]["n_clusters"]
    random_state = cfg["clustering"]["random_state"]

    X = df[pillar_cols].fillna(0.0).values

    km = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
        max_iter=300,
    )
    labels = km.fit_predict(X)

    df = df.copy()
    df["cluster_id"] = labels

    # Compute silhouette score for logging
    sil = silhouette_score(X, labels)
    logger.info(
        "K-Means clustering complete | k=%d | silhouette=%.4f",
        n_clusters, sil,
    )

    return df


def label_clusters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map raw cluster IDs to human-readable labels based on AI score.

    K-Means cluster IDs are arbitrary (0, 1, 2, 3). We map them to
    meaningful labels by ranking clusters on their mean AI Readiness
    Score: the highest-scoring cluster becomes 'AI Leaders', etc.

    The labels and their order come from settings.yaml so they can
    be changed without touching code.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'cluster_id' and 'ai_readiness_score'.

    Returns
    -------
    pd.DataFrame
        With 'cluster_label' and 'cluster_color' columns added.
    """
    cfg = get_config()
    n_clusters = cfg["clustering"]["n_clusters"]

    # Rank clusters by mean AI score (descending)
    cluster_means = (
        df.groupby("cluster_id")["ai_readiness_score"]
        .mean()
        .sort_values(ascending=False)
    )

    # Define ordered label names from config
    label_names = [
        cfg["clustering"]["cluster_labels"][i] for i in range(n_clusters)
    ]

    # Color palette for 4 clusters (Leaders → Laggards)
    cluster_colors = ["#1a9850", "#fee08b", "#f46d43", "#d73027"]

    # Map: cluster_id -> (label, color)
    id_to_label: dict[int, str] = {}
    id_to_color: dict[int, str] = {}
    for rank, cluster_id in enumerate(cluster_means.index):
        if rank < len(label_names):
            id_to_label[cluster_id] = label_names[rank]
            id_to_color[cluster_id] = cluster_colors[rank]

    df = df.copy()
    df["cluster_label"] = df["cluster_id"].map(id_to_label)
    df["cluster_color"] = df["cluster_id"].map(id_to_color)

    # Log cluster composition
    for label in label_names:
        members = df.loc[df["cluster_label"] == label, "state_name"].tolist()
        logger.info("Cluster %-20s (%d states): %s", f"'{label}'", len(members), members)

    return df


# ── Cluster Summary ───────────────────────────────────────────────────────────

def get_cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute mean pillar scores and AI score per cluster.

    This is the key analytical output: it lets us say things like
    "Fast Challengers have strong infrastructure but weak innovation".

    Parameters
    ----------
    df : pd.DataFrame
        Must contain cluster_label and pillar score columns.

    Returns
    -------
    pd.DataFrame
        One row per cluster with mean scores and state count.
    """
    cfg = get_config()
    pillar_score_cols = [f"score_{p}" for p in cfg["pillars"]]
    available = [c for c in pillar_score_cols if c in df.columns]

    agg_cols = available + ["ai_readiness_score"]

    summary = (
        df.groupby("cluster_label")[agg_cols]
        .mean()
        .round(3)
        .reset_index()
    )
    summary["state_count"] = (
        df.groupby("cluster_label")["state_name"]
        .count()
        .values
    )

    # Sort by mean AI score descending
    summary = summary.sort_values("ai_readiness_score", ascending=False)
    logger.info("Cluster summary computed:\n%s", summary.to_string(index=False))

    return summary


# ── Pipeline Entry Point ──────────────────────────────────────────────────────

def run_clustering_pipeline(index_df: pd.DataFrame) -> pd.DataFrame:
    """
    Full clustering pipeline: assign, label, and summarize clusters.

    Parameters
    ----------
    index_df : pd.DataFrame
        Output of index_builder.build_index().

    Returns
    -------
    pd.DataFrame
        index_df enriched with cluster_id, cluster_label, cluster_color.
    """
    cfg = get_config()
    pillar_cols = [f"score_{p}" for p in cfg["pillars"]]
    available_cols = [c for c in pillar_cols if c in index_df.columns]

    logger.info("Running clustering pipeline on %d states...", len(index_df))

    # Validate k choice with elbow analysis
    run_elbow_analysis(index_df, available_cols)

    # Assign and label clusters
    df = assign_clusters(index_df, available_cols)
    df = label_clusters(df)

    # Summary table
    get_cluster_summary(df)

    return df
