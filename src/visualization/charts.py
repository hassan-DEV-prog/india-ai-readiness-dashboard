"""
Chart Library
=============
Reusable, theme-consistent Plotly chart factory functions.

Design Rules
------------
1. Every function returns a plotly.graph_objects.Figure — never renders it
2. All colors come from settings.yaml or the THEME dict below — no hardcoding
3. Every function accepts a `title` parameter for dashboard context
4. Functions are named for what they SHOW, not how they work:
   - plot_state_ranking()  not  make_horizontal_bar()
5. Annotations and insight callouts are optional parameters so the
   same function works in both full and compact dashboard layouts

Public API
----------
plot_state_ranking(df)               -> Figure   bar chart, ranked states
plot_pillar_radar(df, state_name)    -> Figure   radar/spider chart per state
plot_pillar_heatmap(df)              -> Figure   states × pillars heatmap
plot_cluster_scatter(df)             -> Figure   2D scatter coloured by cluster
plot_correlation_heatmap(matrix)     -> Figure   correlation matrix
plot_trend_line(df, col)             -> Figure   single metric over time
plot_gap_bar(df, state_name)         -> Figure   pillar gap bar for one state
plot_top_bottom(df, n)               -> Figure   top-N / bottom-N comparison
plot_kpi_indicator(value, label)     -> Figure   single KPI number card
plot_distribution(df, col)           -> Figure   histogram with median line
"""

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.config_loader import get_config
from src.logger import get_logger

logger = get_logger(__name__)

# ── Theme ─────────────────────────────────────────────────────────────────────
# Single source of visual identity. Change here → changes everywhere.
THEME = {
    "bg_color": "#0F1117",           # Streamlit dark background
    "paper_color": "#1A1D27",        # Card background
    "grid_color": "#2D3040",
    "text_color": "#E8EAF0",
    "subtext_color": "#9BA3B8",
    "accent": "#00BCD4",             # Cyan accent
    "positive": "#1a9850",           # Green
    "negative": "#d73027",           # Red
    "neutral": "#fee08b",            # Yellow
    "font_family": "Inter, system-ui, sans-serif",
    "title_size": 16,
    "axis_size": 12,
    "annotation_size": 11,
}

CLUSTER_COLORS = {
    "AI Leaders": "#1a9850",
    "Fast Challengers": "#91cf60",
    "Emerging Markets": "#fee08b",
    "Lagging Regions": "#d73027",
}


def _base_layout(title: str = "", height: int = 420) -> dict:
    """Return a consistent base layout dict applied to all charts."""
    return dict(
        title=dict(
            text=title,
            font=dict(size=THEME["title_size"], color=THEME["text_color"],
                      family=THEME["font_family"]),
            x=0.01,
            xanchor="left",
        ),
        paper_bgcolor=THEME["paper_color"],
        plot_bgcolor=THEME["bg_color"],
        font=dict(color=THEME["text_color"], family=THEME["font_family"],
                  size=THEME["axis_size"]),
        height=height,
        margin=dict(l=10, r=20, t=50, b=10),
        showlegend=True,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=THEME["grid_color"],
            font=dict(size=11),
        ),
    )


def _styled_axis() -> dict:
    """Return consistent axis styling."""
    return dict(
        gridcolor=THEME["grid_color"],
        linecolor=THEME["grid_color"],
        tickfont=dict(size=11, color=THEME["subtext_color"]),
        zeroline=False,
    )


# ── State Ranking Bar Chart ───────────────────────────────────────────────────

def plot_state_ranking(
    df: pd.DataFrame,
    score_col: str = "ai_readiness_score",
    color_col: str = "cluster_label",
    title: str = "AI Readiness Score — All States",
    n_states: Optional[int] = None,
    height: int = 700,
) -> go.Figure:
    """
    Horizontal bar chart of states ranked by AI Readiness Score.

    Parameters
    ----------
    df : pd.DataFrame
    score_col : str
        Column containing the score to rank by.
    color_col : str
        Column used to colour bars (typically cluster_label).
    title : str
    n_states : int, optional
        If set, shows only top N states.
    height : int

    Returns
    -------
    go.Figure
    """
    plot_df = df.sort_values(score_col, ascending=True)
    if n_states:
        plot_df = plot_df.tail(n_states)

    fig = go.Figure()

    # Legend order matches the severity gradient: Lagging → Emerging → Fast → Leaders
    legend_order = ["Lagging Regions", "Emerging Markets", "Fast Challengers", "AI Leaders"]

    x_max = plot_df[score_col].max()
    x_range = [0, x_max * 1.18]
    x_title = (
        score_col
        .replace("_pct", " %")
        .replace("_per_100", " per 100")
        .replace("_per_million", " per Million")
        .replace("_inr", " (₹)")
        .replace("_kwh", " (kWh)")
        .replace("_", " ")
        .title()
    )

    if color_col in plot_df.columns:
        for cluster_label in legend_order:
            color = CLUSTER_COLORS.get(cluster_label, THEME["accent"])
            subset = plot_df[plot_df[color_col] == cluster_label]
            if subset.empty:
                continue
            fig.add_trace(go.Bar(
                x=subset[score_col],
                y=subset["state_name"],
                orientation="h",
                name=cluster_label,
                marker=dict(color=color, line=dict(color="rgba(0,0,0,0)", width=0)),
                text=subset[score_col].round(1).astype(str),
                textposition="outside",
                textfont=dict(size=10, color=THEME["subtext_color"]),
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    f"{x_title}: %{{x:.1f}}<br>"
                    "<extra></extra>"
                ),
            ))
    else:
        fig.add_trace(go.Bar(
            x=plot_df[score_col],
            y=plot_df["state_name"],
            orientation="h",
            name="States",
            marker=dict(color=THEME["accent"], line=dict(color="rgba(0,0,0,0)", width=0)),
            text=plot_df[score_col].round(1).astype(str),
            textposition="outside",
            textfont=dict(size=10, color=THEME["subtext_color"]),
            hovertemplate=(
                "<b>%{y}</b><br>"
                f"{x_title}: %{{x:.1f}}<br>"
                "<extra></extra>"
            ),
        ))

    layout = _base_layout(title, height)
    layout.update(
        xaxis=dict(**_styled_axis(), title=x_title, range=x_range),
        yaxis=dict(**_styled_axis(), showgrid=False, title=""),
        bargap=0.25,
        barmode="overlay",
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=THEME["grid_color"],
            font=dict(size=11),
            traceorder="normal",
        ),
    )
    fig.update_layout(**layout)

    # Add median reference line
    median_val = plot_df[score_col].median()
    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color=THEME["neutral"],
        line_width=1.5,
        annotation_text=f"Median: {median_val:.1f}",
        annotation_position="top",
        annotation_font=dict(size=10, color=THEME["neutral"]),
    )

    logger.debug("plot_state_ranking: %d states", len(plot_df))
    return fig


# ── Pillar Radar Chart ────────────────────────────────────────────────────────

def plot_pillar_radar(
    df: pd.DataFrame,
    state_names: list[str],
    title: str = "Pillar Scores — Radar View",
    height: int = 420,
) -> go.Figure:
    """
    Spider/radar chart comparing pillar scores for up to 3 states.

    Parameters
    ----------
    df : pd.DataFrame
    state_names : list[str]
        1–3 state names to overlay.
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    cfg = get_config()
    pillar_labels = [cfg["pillars"][p]["label"] for p in cfg["pillars"]]
    score_cols = [f"score_{p}" for p in cfg["pillars"]]

    radar_colors = [THEME["accent"], "#FF7043", "#AB47BC"]
    fig = go.Figure()

    for i, state in enumerate(state_names[:3]):
        row = df[df["state_name"] == state]
        if row.empty:
            logger.warning("State '%s' not found for radar chart", state)
            continue

        values = [row[c].iloc[0] if c in row.columns else 0 for c in score_cols]
        # Close the radar polygon
        values_closed = values + [values[0]]
        labels_closed = pillar_labels + [pillar_labels[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            fillcolor=f"rgba({_hex_to_rgb(radar_colors[i])}, 0.15)",
            line=dict(color=radar_colors[i], width=2),
            name=state,
            hovertemplate="<b>%{theta}</b>: %{r:.3f}<extra></extra>",
        ))

    layout = _base_layout(title, height)
    layout.update(
        polar=dict(
            bgcolor=THEME["bg_color"],
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(size=9, color=THEME["subtext_color"]),
                gridcolor=THEME["grid_color"],
                linecolor=THEME["grid_color"],
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color=THEME["text_color"]),
                gridcolor=THEME["grid_color"],
                linecolor=THEME["grid_color"],
            ),
        ),
        showlegend=True,
    )
    fig.update_layout(**layout)

    logger.debug("plot_pillar_radar: %d states", len(state_names))
    return fig


# ── Pillar Heatmap ────────────────────────────────────────────────────────────

def plot_pillar_heatmap(
    df: pd.DataFrame,
    title: str = "Pillar Score Heatmap — All States",
    height: int = 800,
) -> go.Figure:
    """
    Heatmap of all states × all pillar scores. States sorted by
    AI Readiness Score (top = best).

    Parameters
    ----------
    df : pd.DataFrame
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    cfg = get_config()
    score_cols = [f"score_{p}" for p in cfg["pillars"] if f"score_{p}" in df.columns]
    pillar_labels = [cfg["pillars"][p]["label"] for p in cfg["pillars"]
                     if f"score_{p}" in df.columns]

    plot_df = df.sort_values("ai_readiness_score", ascending=False)
    z_values = plot_df[score_cols].values
    state_labels = plot_df["state_name"].tolist()

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=pillar_labels,
        y=state_labels,
        colorscale=[
            [0.0, "#d73027"],
            [0.25, "#f46d43"],
            [0.5, "#fee08b"],
            [0.75, "#91cf60"],
            [1.0, "#1a9850"],
        ],
        zmin=0,
        zmax=1,
        text=z_values.round(2),
        texttemplate="%{text}",
        textfont=dict(size=9),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "<b>%{x}</b>: %{z:.3f}<br>"
            "<extra></extra>"
        ),
        colorbar=dict(
            title=dict(text="Score", font=dict(color=THEME["subtext_color"], size=11)),
            tickfont=dict(color=THEME["subtext_color"], size=10),
            bgcolor=THEME["paper_color"],
            outlinecolor=THEME["grid_color"],
        ),
    ))

    layout = _base_layout(title, height)
    layout.update(
        xaxis=dict(side="top", tickfont=dict(size=11), showgrid=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=10), showgrid=False),
        margin=dict(l=180, r=20, t=80, b=20),
    )
    fig.update_layout(**layout)

    logger.debug("plot_pillar_heatmap: %d states × %d pillars", len(plot_df), len(score_cols))
    return fig


# ── Cluster Scatter Plot ──────────────────────────────────────────────────────

def plot_cluster_scatter(
    df: pd.DataFrame,
    x_col: str = "score_internet",
    y_col: str = "score_economy",
    title: str = "State Clusters — AI Readiness",
    height: int = 500,
) -> go.Figure:
    """
    2D scatter plot with states coloured by cluster.

    Parameters
    ----------
    df : pd.DataFrame
    x_col : str
        Pillar score for x-axis.
    y_col : str
        Pillar score for y-axis.
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    cfg = get_config()

    def _label(col: str) -> str:
        """Convert score_internet → 'Internet Readiness'"""
        key = col.replace("score_", "")
        return cfg["pillars"].get(key, {}).get("label", col)

    fig = go.Figure()

    for cluster_label, color in CLUSTER_COLORS.items():
        subset = df[df["cluster_label"] == cluster_label] if "cluster_label" in df.columns \
            else df

        if subset.empty:
            continue

        fig.add_trace(go.Scatter(
            x=subset[x_col] if x_col in subset.columns else [],
            y=subset[y_col] if y_col in subset.columns else [],
            mode="markers+text",
            name=cluster_label,
            text=subset["state_name"].str.split().str[0],  # First word only to avoid crowding
            textposition="top center",
            textfont=dict(size=8, color=THEME["subtext_color"]),
            marker=dict(
                size=subset["ai_readiness_score"].values / 4
                if "ai_readiness_score" in subset.columns else 10,
                color=color,
                line=dict(color="white", width=0.5),
                opacity=0.85,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{_label(x_col)}: %{{x:.3f}}<br>"
                f"{_label(y_col)}: %{{y:.3f}}<br>"
                "AI Score: %{marker.size:.0f}<br>"
                "<extra></extra>"
            ),
            customdata=subset["ai_readiness_score"].values
            if "ai_readiness_score" in subset.columns else None,
        ))

    layout = _base_layout(title, height)
    layout.update(
        xaxis=dict(**_styled_axis(), title=_label(x_col), range=[-0.05, 1.1]),
        yaxis=dict(**_styled_axis(), title=_label(y_col), range=[-0.05, 1.1]),
    )
    fig.update_layout(**layout)
    return fig


# ── Correlation Heatmap ───────────────────────────────────────────────────────

def plot_correlation_heatmap(
    corr_matrix: pd.DataFrame,
    title: str = "Pillar Correlation Matrix (Spearman ρ)",
    height: int = 420,
) -> go.Figure:
    """
    Annotated correlation heatmap for a square correlation matrix.

    Parameters
    ----------
    corr_matrix : pd.DataFrame
        Output of correlation.compute_correlation_matrix().
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    z = corr_matrix.values
    labels = corr_matrix.columns.tolist()

    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=labels,
        y=labels,
        colorscale=[
            [0.0, "#d73027"],
            [0.5, THEME["paper_color"]],
            [1.0, "#1a9850"],
        ],
        zmin=-1,
        zmax=1,
        text=z.round(2),
        texttemplate="%{text}",
        textfont=dict(size=12, color=THEME["text_color"]),
        hovertemplate="<b>%{y}</b> × <b>%{x}</b>: %{z:.3f}<extra></extra>",
        showscale=True,
        colorbar=dict(
            title=dict(text="ρ", font=dict(color=THEME["subtext_color"])),
            tickfont=dict(color=THEME["subtext_color"]),
            bgcolor=THEME["paper_color"],
            outlinecolor=THEME["grid_color"],
            len=0.8,
        ),
    ))

    layout = _base_layout(title, height)
    layout.update(
        xaxis=dict(tickfont=dict(size=10), showgrid=False, side="bottom"),
        yaxis=dict(tickfont=dict(size=10), showgrid=False, autorange="reversed"),
        margin=dict(l=160, r=20, t=60, b=120),
    )
    fig.update_layout(**layout)
    return fig


# ── Gap Bar Chart ─────────────────────────────────────────────────────────────

def plot_gap_bar(
    df: pd.DataFrame,
    state_name: str,
    title: Optional[str] = None,
    height: int = 380,
) -> go.Figure:
    """
    Bar chart showing each pillar's score vs this state's own mean.

    Visually answers: 'Which pillar is dragging this state down?'

    Parameters
    ----------
    df : pd.DataFrame
    state_name : str
    title : str, optional
    height : int

    Returns
    -------
    go.Figure
    """
    cfg = get_config()
    row = df[df["state_name"] == state_name]
    if row.empty:
        logger.warning("State '%s' not found for gap bar", state_name)
        return go.Figure()

    row = row.iloc[0]
    pillar_labels = [cfg["pillars"][p]["label"] for p in cfg["pillars"]
                     if f"score_{p}" in df.columns]
    scores = [row.get(f"score_{p}", 0) for p in cfg["pillars"]
              if f"score_{p}" in df.columns]
    state_mean = row.get("state_pillar_mean", pd.Series(scores).mean())

    bar_colors = [
        THEME["positive"] if s >= state_mean else THEME["negative"]
        for s in scores
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pillar_labels,
        y=scores,
        marker_color=bar_colors,
        text=[f"{s:.2f}" for s in scores],
        textposition="outside",
        hovertemplate="<b>%{x}</b>: %{y:.3f}<extra></extra>",
        name="Pillar Score",
    ))

    # State mean reference line
    fig.add_hline(
        y=state_mean,
        line_dash="dash",
        line_color=THEME["neutral"],
        line_width=2,
        annotation_text=f"State Average: {state_mean:.2f}",
        annotation_position="top right",
        annotation_font=dict(size=10, color=THEME["neutral"]),
    )

    layout = _base_layout(title or f"{state_name} — Pillar Score Breakdown", height)
    layout.update(
        xaxis=dict(**_styled_axis(), showgrid=False),
        yaxis=dict(**_styled_axis(), range=[0, 1.1], title="Score (0–1)"),
        showlegend=False,
    )
    fig.update_layout(**layout)
    return fig


# ── Top / Bottom Comparison ───────────────────────────────────────────────────

def plot_top_bottom(
    df: pd.DataFrame,
    n: int = 5,
    score_col: str = "ai_readiness_score",
    title: str = "Top & Bottom States",
    height: int = 420,
) -> go.Figure:
    """
    Side-by-side comparison of top-N and bottom-N states.

    Parameters
    ----------
    df : pd.DataFrame
    n : int
    score_col : str
    title : str
    height : int

    Returns
    -------
    go.Figure
    """
    top = df.nlargest(n, score_col)[["state_name", score_col]]
    bottom = df.nsmallest(n, score_col)[["state_name", score_col]]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f"Top {n}", f"Bottom {n}"),
    )

    fig.add_trace(
        go.Bar(
            x=top[score_col],
            y=top["state_name"],
            orientation="h",
            marker_color=THEME["positive"],
            text=top[score_col].round(1),
            textposition="outside",
            name="Top States",
            hovertemplate="<b>%{y}</b>: %{x:.1f}<extra></extra>",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=bottom[score_col],
            y=bottom["state_name"],
            orientation="h",
            marker_color=THEME["negative"],
            text=bottom[score_col].round(1),
            textposition="outside",
            name="Bottom States",
            hovertemplate="<b>%{y}</b>: %{x:.1f}<extra></extra>",
        ),
        row=1, col=2,
    )

    layout = _base_layout(title, height)
    layout.update(
        xaxis=dict(**_styled_axis(), range=[0, 105], showgrid=True),
        xaxis2=dict(**_styled_axis(), range=[0, 105], showgrid=True),
        yaxis=dict(**_styled_axis(), showgrid=False),
        yaxis2=dict(**_styled_axis(), showgrid=False),
        showlegend=False,
        margin=dict(l=130, r=60, t=60, b=20),
    )
    # Style subplot titles
    for annotation in fig.layout.annotations:
        annotation.font.color = THEME["subtext_color"]
        annotation.font.size = 12

    fig.update_layout(**layout)
    return fig


# ── KPI Indicator ─────────────────────────────────────────────────────────────

def plot_kpi_indicator(
    value: float,
    label: str,
    reference: Optional[float] = None,
    suffix: str = "",
    height: int = 160,
) -> go.Figure:
    """
    Single large KPI number card.

    Parameters
    ----------
    value : float
        The metric value to display.
    label : str
        Descriptive label shown below the number.
    reference : float, optional
        Reference value for delta display (e.g., national average).
    suffix : str
        Unit suffix (e.g., '%', '/100').
    height : int

    Returns
    -------
    go.Figure
    """
    fig = go.Figure()
    fig.add_trace(go.Indicator(
        mode="number+delta" if reference is not None else "number",
        value=value,
        number=dict(
            suffix=suffix,
            font=dict(size=42, color=THEME["accent"],
                      family=THEME["font_family"]),
        ),
        delta=dict(
            reference=reference,
            valueformat=".1f",
            font=dict(size=14),
            increasing=dict(color=THEME["positive"]),
            decreasing=dict(color=THEME["negative"]),
        ) if reference is not None else None,
        title=dict(
            text=label,
            font=dict(size=13, color=THEME["subtext_color"],
                      family=THEME["font_family"]),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=THEME["paper_color"],
        plot_bgcolor=THEME["bg_color"],
        height=height,
        margin=dict(l=20, r=20, t=20, b=10),
    )
    return fig


# ── Distribution Histogram ────────────────────────────────────────────────────

def plot_distribution(
    df: pd.DataFrame,
    col: str,
    title: Optional[str] = None,
    height: int = 340,
) -> go.Figure:
    """
    Histogram of a single metric with median reference line.

    Parameters
    ----------
    df : pd.DataFrame
    col : str
        Column to plot.
    title : str, optional
    height : int

    Returns
    -------
    go.Figure
    """
    values = df[col].dropna()
    median_val = values.median()

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=values,
        nbinsx=15,
        marker=dict(
            color=THEME["accent"],
            opacity=0.75,
            line=dict(color=THEME["bg_color"], width=0.5),
        ),
        hovertemplate="Range: %{x}<br>Count: %{y}<extra></extra>",
        name=col.replace("_", " ").title(),
    ))

    fig.add_vline(
        x=median_val,
        line_dash="dash",
        line_color=THEME["neutral"],
        line_width=2,
        annotation_text=f"Median: {median_val:.1f}",
        annotation_font=dict(color=THEME["neutral"], size=11),
        annotation_position="top",
    )

    layout = _base_layout(title or col.replace("_", " ").title(), height)
    layout.update(
        xaxis=dict(**_styled_axis(), title=col.replace("_", " ").title()),
        yaxis=dict(**_styled_axis(), title="Number of States"),
        showlegend=False,
    )
    fig.update_layout(**layout)
    return fig


# ── Utilities ─────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#RRGGBB' to 'R,G,B' string for rgba() use."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"{r},{g},{b}"
