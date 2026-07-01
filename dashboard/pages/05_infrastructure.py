"""
Page 5 — Infrastructure
=========================
Business question: Is India's physical infrastructure
ready to support an AI-powered economy?
"""

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard.data_loader import get_dashboard_data
from src.visualization.charts import (
    plot_state_ranking, plot_distribution, THEME, _base_layout, _styled_axis,
)

st.set_page_config(page_title="Infrastructure | India AI Readiness", layout="wide", page_icon="⚡")
st.markdown("""<style>
    .stApp{background-color:#0F1117}
    [data-testid="stSidebar"]{background-color:#1A1D27;border-right:1px solid #2D3040}
    [data-testid="stMetric"]{background-color:#1A1D27;border:1px solid #2D3040;border-radius:8px;padding:16px}
    [data-testid="stMetricValue"]{color:#00BCD4}
    .insight-box{background-color:#1A1D27;border-left:3px solid #FF9800;border-radius:4px;padding:12px 16px;margin:8px 0;color:#E8EAF0;font-size:.9rem;line-height:1.6}
    .section-header{color:#FF9800;font-size:.75rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px;margin-top:24px}
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    .stPlotlyChart{border:1px solid #2D3040;border-radius:8px}
</style>""", unsafe_allow_html=True)

with st.spinner("Loading..."):
    data = get_dashboard_data()
df = data["index"]

st.markdown("<h2 style='color:#E8EAF0'>⚡ Infrastructure</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#9BA3B8'>Electricity availability and per-capita power consumption — the physical backbone of AI deployment.</p>", unsafe_allow_html=True)
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    avg_elec = df["electrification_pct"].mean()
    st.metric("Avg Electrification", f"{avg_elec:.1f}%")
with k2:
    fully_electrified = (df["electrification_pct"] >= 99.9).sum()
    st.metric("Fully Electrified States", f"{fully_electrified}", "≥ 99.9%")
with k3:
    avg_power = df["per_capita_power_consumption_kwh"].mean()
    st.metric("Avg Power Consumption", f"{avg_power:.0f} kWh/capita")
with k4:
    top_power = df.loc[df["per_capita_power_consumption_kwh"].idxmax(), "state_name"]
    top_kwh = df["per_capita_power_consumption_kwh"].max()
    st.metric("Highest Consumption", top_power, f"{top_kwh:.0f} kWh")

st.divider()

# ── Infrastructure Pillar Score Ranking ───────────────────────────────────────
st.markdown("<p class='section-header'>Infrastructure Pillar Score</p>", unsafe_allow_html=True)
st.caption("Combined score from electrification rate and per-capita power consumption, normalized to [0,1].")
st.plotly_chart(
    plot_state_ranking(
        df, score_col="score_infrastructure",
        color_col="cluster_label",
        title="Infrastructure Pillar Score — All States",
        height=660,
    ),
    use_container_width=True,
)

# ── Power Consumption vs AI Score ────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Power Consumption vs AI Readiness</p>", unsafe_allow_html=True)
st.caption("High per-capita power consumption correlates with economic development, "
           "which in turn predicts AI readiness. But the relationship is not linear — "
           "some states consume little power but score well on innovation.")

power_df = df[["state_name", "per_capita_power_consumption_kwh",
               "ai_readiness_score", "cluster_label",
               "electrification_pct"]].copy()
power_df = power_df.sort_values("per_capita_power_consumption_kwh", ascending=True)

fig_pw = go.Figure()
cluster_colors = {
    "AI Leaders": "#1a9850", "Fast Challengers": "#91cf60",
    "Emerging Markets": "#fee08b", "Lagging Regions": "#d73027",
}
for cluster, color in cluster_colors.items():
    sub = power_df[power_df["cluster_label"] == cluster]
    if sub.empty:
        continue
    fig_pw.add_trace(go.Bar(
        name=cluster,
        y=sub["state_name"],
        x=sub["per_capita_power_consumption_kwh"],
        orientation="h",
        marker_color=color,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Power: %{x:.0f} kWh/capita<br>"
            "<extra></extra>"
        ),
    ))

layout = _base_layout("Per-Capita Power Consumption (kWh) by State", height=680)
layout.update(
    barmode="stack",
    xaxis=dict(**_styled_axis(), title="kWh per Capita"),
    yaxis=dict(**_styled_axis(), showgrid=False),
)
fig_pw.update_layout(**layout)
st.plotly_chart(fig_pw, use_container_width=True)

# ── Electrification Map ───────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.markdown("<p class='section-header'>Electrification Rate</p>", unsafe_allow_html=True)
    not_full = df[df["electrification_pct"] < 99.9].sort_values("electrification_pct")
    if not_full.empty:
        st.success("All states have achieved near-universal electrification (≥99.9%). "
                   "This pillar has near-zero entropy weight — it no longer discriminates between states.")
    else:
        st.plotly_chart(
            plot_state_ranking(
                not_full, score_col="electrification_pct",
                color_col="cluster_label",
                title="States Below 99.9% Electrification",
                height=400,
            ),
            use_container_width=True,
        )

with c2:
    st.markdown("<p class='section-header'>Power Consumption Distribution</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_distribution(
            df, "per_capita_power_consumption_kwh",
            title="Per-Capita Power Consumption — Distribution",
        ),
        use_container_width=True,
    )

# ── Analytical Insight ────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Why Infrastructure Has the Lowest Weight</p>", unsafe_allow_html=True)

low_entropy_threshold = 99.0
pct_above = (df["electrification_pct"] >= low_entropy_threshold).mean() * 100

st.markdown(
    f"<div class='insight-box'>"
    f"<b>Entropy weighting decision:</b> {pct_above:.0f}% of states have electrification ≥ 99%. "
    f"When all states score similarly on a metric, it carries no information for discrimination "
    f"— its entropy approaches 1.0 and its weight approaches 0. "
    f"Infrastructure therefore receives the lowest entropy weight in this index. "
    f"This is <b>analytically correct, not a design flaw</b>: electrification is now a "
    f"universal baseline, not a differentiator. The discriminating infrastructure metric "
    f"going forward will be <b>data center density and fiber coverage</b> — "
    f"recommended additions for the next version of this index."
    f"</div>",
    unsafe_allow_html=True,
)
