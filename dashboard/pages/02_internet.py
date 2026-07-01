"""
Page 2 — Internet Infrastructure
==================================
Business question: How does internet readiness vary across states,
and what is the rural–urban connectivity divide?
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard.data_loader import get_dashboard_data
from src.visualization.charts import (
    plot_distribution,
    plot_state_ranking,
    plot_kpi_indicator,
    THEME,
    _base_layout,
    _styled_axis,
)

st.set_page_config(page_title="Internet | India AI Readiness", layout="wide", page_icon="🌐")

st.markdown("""<style>
    .stApp{background-color:#0F1117}
    [data-testid="stSidebar"]{background-color:#1A1D27;border-right:1px solid #2D3040}
    [data-testid="stMetric"]{background-color:#1A1D27;border:1px solid #2D3040;border-radius:8px;padding:16px}
    [data-testid="stMetricValue"]{color:#00BCD4}
    .insight-box{background-color:#1A1D27;border-left:3px solid #00BCD4;border-radius:4px;padding:12px 16px;margin:8px 0;color:#E8EAF0;font-size:.9rem;line-height:1.6}
    .section-header{color:#00BCD4;font-size:.75rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px;margin-top:24px}
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    .stPlotlyChart{border:1px solid #2D3040;border-radius:8px}
</style>""", unsafe_allow_html=True)

with st.spinner("Loading..."):
    data = get_dashboard_data()
df = data["index"]

st.markdown("<h2 style='color:#E8EAF0'>🌐 Internet Infrastructure</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#9BA3B8'>Broadband density, penetration rates, and the rural–urban digital divide.</p>", unsafe_allow_html=True)
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Avg Internet Penetration", f"{df['internet_penetration_pct'].mean():.1f}%")
with k2:
    st.metric("Avg Broadband /100", f"{df['broadband_subscribers_per_100'].mean():.1f}")
with k3:
    rural_avg = df["rural_internet_pct"].mean()
    urban_avg = df["urban_internet_pct"].mean()
    st.metric("Avg Rural Internet", f"{rural_avg:.1f}%", f"{rural_avg - urban_avg:.1f}% vs urban")
with k4:
    top_state = df.loc[df["internet_penetration_pct"].idxmax(), "state_name"]
    top_pct = df["internet_penetration_pct"].max()
    st.metric("Most Connected State", top_state, f"{top_pct:.1f}%")

st.divider()

# ── Internet Penetration Ranking ──────────────────────────────────────────────
st.markdown("<p class='section-header'>Internet Penetration by State</p>", unsafe_allow_html=True)
st.plotly_chart(
    plot_state_ranking(
        df,
        score_col="internet_penetration_pct",
        color_col="cluster_label",
        title="Internet Penetration (%) — All States",
        height=660,
    ),
    use_container_width=True,
)

# ── Rural vs Urban Divide ─────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Rural vs Urban Internet Divide</p>", unsafe_allow_html=True)
st.caption("The gap between rural and urban internet access reveals digital infrastructure inequality within states.")

rural_urban_df = df[["state_name", "rural_internet_pct", "urban_internet_pct"]].copy()
rural_urban_df = rural_urban_df.sort_values("rural_internet_pct", ascending=True)
rural_urban_df["gap"] = rural_urban_df["urban_internet_pct"] - rural_urban_df["rural_internet_pct"]

fig_ru = go.Figure()
fig_ru.add_trace(go.Bar(
    name="Rural",
    y=rural_urban_df["state_name"],
    x=rural_urban_df["rural_internet_pct"],
    orientation="h",
    marker_color="#1a9850",
    hovertemplate="<b>%{y}</b><br>Rural: %{x:.1f}%<extra></extra>",
))
fig_ru.add_trace(go.Bar(
    name="Urban",
    y=rural_urban_df["state_name"],
    x=rural_urban_df["urban_internet_pct"],
    orientation="h",
    marker_color="#2196F3",
    opacity=0.6,
    hovertemplate="<b>%{y}</b><br>Urban: %{x:.1f}%<extra></extra>",
))
layout = _base_layout("Rural vs Urban Internet Penetration (%)", height=680)
layout.update(
    barmode="overlay",
    xaxis=dict(**_styled_axis(), title="Internet Penetration (%)", range=[0, 105]),
    yaxis=dict(**_styled_axis(), showgrid=False),
    legend=dict(orientation="h", y=1.02, x=0),
)
fig_ru.update_layout(**layout)
st.plotly_chart(fig_ru, use_container_width=True)

# ── Insight ───────────────────────────────────────────────────────────────────
max_gap_row = rural_urban_df.loc[rural_urban_df["gap"].idxmax()]
min_gap_row = rural_urban_df.loc[rural_urban_df["gap"].idxmin()]
st.markdown(
    f"<div class='insight-box'>"
    f"<b>Widest rural–urban gap:</b> {max_gap_row['state_name']} "
    f"({max_gap_row['gap']:.1f} percentage points). "
    f"<b>Most equitable:</b> {min_gap_row['state_name']} "
    f"(gap of {min_gap_row['gap']:.1f} pp) — suggesting that smaller, "
    f"denser states and UTs achieve more uniform connectivity."
    f"</div>",
    unsafe_allow_html=True,
)

# ── Broadband vs Internet Penetration Scatter ─────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Broadband Density vs Internet Penetration</p>", unsafe_allow_html=True)
st.caption("States above the trend line have high penetration relative to their broadband infrastructure — often driven by mobile internet.")

import plotly.express as px
fig_scatter = px.scatter(
    df,
    x="broadband_subscribers_per_100",
    y="internet_penetration_pct",
    text="state_name",
    color="cluster_label",
    color_discrete_map={
        "AI Leaders": "#1a9850",
        "Fast Challengers": "#91cf60",
        "Emerging Markets": "#fee08b",
        "Lagging Regions": "#d73027",
    },
    trendline="ols",
    trendline_color_override="#9BA3B8",
    title="Broadband Subscribers per 100 vs Internet Penetration (%)",
    labels={
        "broadband_subscribers_per_100": "Broadband Subscribers per 100",
        "internet_penetration_pct": "Internet Penetration (%)",
        "cluster_label": "Cluster",
    },
    height=480,
)
fig_scatter.update_traces(
    textposition="top center",
    textfont=dict(size=8, color=THEME["subtext_color"]),
    selector=dict(mode="markers+text"),
)
fig_scatter.update_layout(
    paper_bgcolor=THEME["paper_color"],
    plot_bgcolor=THEME["bg_color"],
    font=dict(color=THEME["text_color"]),
    xaxis=dict(**_styled_axis()),
    yaxis=dict(**_styled_axis()),
)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Distribution ──────────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.markdown("<p class='section-header'>Distribution: Internet Penetration</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_distribution(df, "internet_penetration_pct",
                          title="Internet Penetration — Distribution"),
        use_container_width=True,
    )
with c2:
    st.markdown("<p class='section-header'>Distribution: Broadband per 100</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_distribution(df, "broadband_subscribers_per_100",
                          title="Broadband Subscribers per 100 — Distribution"),
        use_container_width=True,
    )
