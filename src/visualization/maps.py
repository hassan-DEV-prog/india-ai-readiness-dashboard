"""
Map Visualization
=================
Choropleth and bubble map functions for state-level geographic
visualization of AI readiness metrics.

Why Plotly Choropleth over Folium?
-----------------------------------
Folium produces HTML maps that are harder to embed in Streamlit
with consistent theming. Plotly choropleths integrate natively
with the rest of our chart library and support the same dark theme.
Folium is retained as a fallback if GeoJSON loading fails.

GeoJSON Note
------------
The India state boundaries GeoJSON must be placed at:
  data/external/india_states.geojson

A suitable file is available from:
  https://github.com/Subhash9325/GeoJson-Data-of-Indian-States

The 'NAME_1' property in that file is used as the state name key
for matching against our canonical state names.

Public API
----------
load_geojson()                          -> dict | None
plot_choropleth(df, value_col)          -> go.Figure
plot_bubble_map(df, size_col, color_col)-> go.Figure
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config.config_loader import get_config, resolve_path
from src.logger import get_logger
from src.visualization.charts import THEME, _base_layout

logger = get_logger(__name__)

# Property key in the GeoJSON that holds the state name
_GEOJSON_NAME_PROPERTY = "NAME_1"


# ── GeoJSON Loader ────────────────────────────────────────────────────────────

def load_geojson() -> Optional[dict]:
    """
    Load the India state boundaries GeoJSON file.

    Returns
    -------
    dict
        Parsed GeoJSON as a Python dict.
    None
        If the file is not found (map will be skipped gracefully).
    """
    cfg = get_config()
    geojson_path = (
        resolve_path(cfg["paths"]["data_external"])
        / cfg["data_files"]["india_geojson"]
    )

    if not geojson_path.exists():
        logger.warning(
            "GeoJSON not found at %s. "
            "Map visualizations will be disabled. "
            "Download from: https://github.com/Subhash9325/GeoJson-Data-of-Indian-States",
            geojson_path,
        )
        return None

    with geojson_path.open("r", encoding="utf-8") as f:
        geojson = json.load(f)

    feature_count = len(geojson.get("features", []))
    logger.info("GeoJSON loaded: %d state features", feature_count)
    return geojson


# ── Choropleth Map ────────────────────────────────────────────────────────────

def plot_choropleth(
    df: pd.DataFrame,
    value_col: str = "ai_readiness_score",
    geojson: Optional[dict] = None,
    title: str = "India AI Readiness — State Choropleth",
    color_scale: str = "RdYlGn",
    height: int = 580,
) -> go.Figure:
    """
    Choropleth map of India coloured by a state-level metric.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain 'state_name' and value_col.
    value_col : str
        Column to use for colour encoding.
    geojson : dict, optional
        Pre-loaded GeoJSON. If None, attempts to load from disk.
    title : str
    color_scale : str
        Plotly colorscale name. 'RdYlGn' gives red→yellow→green.
    height : int

    Returns
    -------
    go.Figure
        Choropleth figure, or a fallback bar chart if GeoJSON unavailable.
    """
    if geojson is None:
        geojson = load_geojson()

    if geojson is None:
        logger.warning("Falling back to bar chart — GeoJSON not available")
        return _fallback_bar(df, value_col, title, height)

    col_label = value_col.replace("_", " ").title()

    fig = px.choropleth(
        df,
        geojson=geojson,
        locations="state_name",
        featureidkey=f"properties.{_GEOJSON_NAME_PROPERTY}",
        color=value_col,
        color_continuous_scale=color_scale,
        hover_name="state_name",
        hover_data={
            value_col: ":.2f",
            "ai_readiness_score_rank": True,
            "cluster_label": True,
        } if all(c in df.columns for c in ["ai_readiness_score_rank", "cluster_label"]) else {},
        labels={value_col: col_label},
    )

    cfg = get_config()
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor=THEME["bg_color"],
        lakecolor=THEME["bg_color"],
        landcolor=THEME["paper_color"],
    )

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=THEME["title_size"], color=THEME["text_color"]),
            x=0.01,
        ),
        paper_bgcolor=THEME["paper_color"],
        geo=dict(bgcolor=THEME["bg_color"]),
        coloraxis_colorbar=dict(
            title=col_label[:12],
            titlefont=dict(color=THEME["subtext_color"], size=11),
            tickfont=dict(color=THEME["subtext_color"], size=10),
            bgcolor=THEME["paper_color"],
            outlinecolor=THEME["paper_color"],
        ),
        height=height,
        margin=dict(l=0, r=0, t=50, b=0),
    )

    logger.debug("plot_choropleth: %s, %d states", value_col, len(df))
    return fig


# ── Bubble Map ────────────────────────────────────────────────────────────────

def plot_bubble_map(
    df: pd.DataFrame,
    size_col: str = "ai_readiness_score",
    color_col: str = "cluster_label",
    title: str = "India AI Readiness — Bubble Map",
    height: int = 580,
) -> go.Figure:
    """
    Bubble map with approximate state centroids. Bubble size encodes
    one metric, colour encodes another.

    Note: State centroids are approximated. A full centroid dataset
    would come from GeoJSON centroid computation; these are sufficient
    for dashboard purposes.

    Parameters
    ----------
    df : pd.DataFrame
    size_col : str
        Column for bubble size.
    color_col : str
        Column for bubble colour (typically cluster_label).
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    from src.visualization.charts import CLUSTER_COLORS

    # Approximate centroids for Indian states
    STATE_CENTROIDS = {
        "Andaman and Nicobar Islands": (11.7, 92.7),
        "Andhra Pradesh": (15.9, 79.7),
        "Arunachal Pradesh": (28.2, 94.7),
        "Assam": (26.2, 92.9),
        "Bihar": (25.1, 85.3),
        "Chandigarh": (30.7, 76.8),
        "Chhattisgarh": (21.3, 81.9),
        "Dadra and Nagar Haveli and Daman and Diu": (20.4, 72.8),
        "NCT of Delhi": (28.7, 77.1),
        "Goa": (15.3, 74.1),
        "Gujarat": (22.3, 71.2),
        "Haryana": (29.1, 76.1),
        "Himachal Pradesh": (31.1, 77.2),
        "Jammu and Kashmir": (33.7, 76.9),
        "Jharkhand": (23.6, 85.3),
        "Karnataka": (15.3, 75.7),
        "Kerala": (10.9, 76.3),
        "Ladakh": (34.2, 77.6),
        "Lakshadweep": (10.6, 72.6),
        "Madhya Pradesh": (22.9, 78.7),
        "Maharashtra": (19.7, 75.7),
        "Manipur": (24.7, 93.9),
        "Meghalaya": (25.5, 91.4),
        "Mizoram": (23.2, 92.9),
        "Nagaland": (26.2, 94.6),
        "Odisha": (20.9, 85.1),
        "Puducherry": (11.9, 79.8),
        "Punjab": (31.1, 75.3),
        "Rajasthan": (27.0, 74.2),
        "Sikkim": (27.5, 88.5),
        "Tamil Nadu": (11.1, 78.7),
        "Telangana": (17.4, 79.1),
        "Tripura": (23.9, 91.5),
        "Uttarakhand": (30.1, 79.3),
        "Uttar Pradesh": (26.8, 80.9),
        "West Bengal": (22.9, 87.9),
    }

    plot_df = df.copy()
    plot_df["lat"] = plot_df["state_name"].map(lambda s: STATE_CENTROIDS.get(s, (None, None))[0])
    plot_df["lon"] = plot_df["state_name"].map(lambda s: STATE_CENTROIDS.get(s, (None, None))[1])
    plot_df = plot_df.dropna(subset=["lat", "lon"])

    if color_col == "cluster_label" and "cluster_label" in plot_df.columns:
        plot_df["_color"] = plot_df["cluster_label"].map(CLUSTER_COLORS)
    else:
        plot_df["_color"] = THEME["accent"]

    fig = go.Figure()

    # Group by cluster for legend
    if "cluster_label" in plot_df.columns:
        for cluster, color in CLUSTER_COLORS.items():
            subset = plot_df[plot_df["cluster_label"] == cluster]
            if subset.empty:
                continue
            _add_bubble_trace(fig, subset, size_col, color, cluster)
    else:
        _add_bubble_trace(fig, plot_df, size_col, THEME["accent"], "States")

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=THEME["title_size"], color=THEME["text_color"]),
            x=0.01,
        ),
        paper_bgcolor=THEME["paper_color"],
        geo=dict(
            scope="asia",
            center=dict(lat=22, lon=82),
            projection_scale=4.5,
            bgcolor=THEME["bg_color"],
            lakecolor=THEME["bg_color"],
            landcolor="#1E2030",
            showcoastlines=True,
            coastlinecolor=THEME["grid_color"],
            showland=True,
            showcountries=True,
            countrycolor=THEME["grid_color"],
        ),
        height=height,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=THEME["text_color"], size=11),
        ),
    )

    logger.debug("plot_bubble_map: %d states plotted", len(plot_df))
    return fig


def _add_bubble_trace(
    fig: go.Figure,
    subset: pd.DataFrame,
    size_col: str,
    color: str,
    name: str,
) -> None:
    """Add a single cluster's bubble trace to the figure."""
    sizes = subset[size_col].fillna(1) if size_col in subset.columns else 10

    fig.add_trace(go.Scattergeo(
        lat=subset["lat"],
        lon=subset["lon"],
        text=subset["state_name"],
        mode="markers",
        marker=dict(
            size=(sizes / sizes.max() * 30).clip(lower=4),
            color=color,
            opacity=0.80,
            line=dict(color="white", width=0.5),
        ),
        name=name,
        hovertemplate=(
            "<b>%{text}</b><br>"
            f"{size_col.replace('_', ' ').title()}: %{{marker.size:.0f}}<br>"
            "<extra></extra>"
        ),
    ))


# ── Fallback Chart ────────────────────────────────────────────────────────────

def _fallback_bar(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    height: int,
) -> go.Figure:
    """
    Horizontal bar chart used when GeoJSON is unavailable.
    Preserves functionality without geographic rendering.
    """
    from src.visualization.charts import plot_state_ranking
    logger.info("Using fallback bar chart for map: %s", value_col)
    return plot_state_ranking(df, score_col=value_col, title=title, height=height)
