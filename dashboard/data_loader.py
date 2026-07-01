"""
Dashboard Data Loader
=====================
Runs the full ETL + feature engineering + analysis pipeline
and caches the result for the Streamlit session.

Every dashboard page imports get_dashboard_data() from here.
The pipeline runs exactly once per session — subsequent page
navigations return the cached DataFrame instantly.

Usage
-----
    from dashboard.data_loader import get_dashboard_data
    data = get_dashboard_data()
    df = data["index"]
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure project root is on the path when running via streamlit
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.etl.loader import load_all_raw
from src.etl.cleaner import clean_all
from src.etl.merger import run_merge_pipeline
from src.features.index_builder import build_index
from src.analysis.clustering import run_clustering_pipeline
from src.analysis.correlation import run_correlation_analysis
from src.analysis.gap_analysis import run_gap_analysis
from src.logger import get_logger

logger = get_logger(__name__)


@st.cache_data(show_spinner=False)
def get_dashboard_data() -> dict:
    """
    Run the full pipeline and return all analysis outputs.

    Cached with st.cache_data — runs once per Streamlit session.
    Subsequent calls return the cached dict instantly.

    Returns
    -------
    dict with keys:
        index         : pd.DataFrame  — full enriched index (all pages read this)
        corr_results  : dict          — spearman/pearson matrices + insights
        opportunity   : pd.DataFrame  — latent potential states
        entropy_weights: dict[str, float]
    """
    logger.info("Pipeline cache miss — running full ETL + analysis...")

    # ETL
    raw = load_all_raw()
    cleaned = clean_all(raw)
    master = run_merge_pipeline(cleaned, save=False)

    # Feature engineering
    index_df = build_index(master)

    # Extract entropy weights before clustering enriches the df
    pillar_cols = [c for c in index_df.columns if c.startswith("weight_")]
    entropy_weights = {
        col.replace("weight_", ""): float(index_df[col].iloc[0])
        for col in pillar_cols
    }

    # Analysis
    clustered = run_clustering_pipeline(index_df)
    corr_results = run_correlation_analysis(clustered)
    gap_results = run_gap_analysis(clustered)

    final_df = gap_results["gap_df"]

    # Persist processed file for Power BI
    processed_dir = _PROJECT_ROOT / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(processed_dir / "ai_readiness_index.csv", index=False)

    logger.info("Pipeline complete. %d states × %d columns.", len(final_df), len(final_df.columns))

    return {
        "index": final_df,
        "corr_results": corr_results,
        "opportunity": gap_results["opportunity_states"],
        "entropy_weights": entropy_weights,
    }
