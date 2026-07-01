"""
Page 4 — Innovation Ecosystem
==============================
Business question: Where is startup activity concentrated,
and which states have talent without an innovation outlet?
"""

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard.data_loader import get_dashboard_data
from src.visualization.charts import (
    plot_state_ranking, plot_distribution, THEME, _styled_axis,
)

st.set_page_config(page_title="Innovation | India AI Readiness", layout="wide", page_icon="💡")
st.markdown("""<style>
    .stApp{background-color:#0F1117}
    [data-testid="stSidebar"]{background-color:#1A1D27;border-right:1px solid #2D3040}
    [data-testid="stMetric"]{background-color:#1A1D27;border:1px solid #2D3040;border-radius:8px;padding:16px}
    [data-testid="stMetricValue"]{color:#00BCD4}
    .insight-box{background-color:#1A1D27;border-left:3px solid #9C27B0;border-radius:4px;padding:12px 16px;margin:8px 0;color:#E8EAF0;font-size:.9rem;line-height:1.6}
    .section-header{color:#9C27B0;font-size:.75rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px;margin-top:24px}
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    .stPlotlyChart{border:1px solid #2D3040;border-radius:8px}
</style>""", unsafe_allow_html=True)

with st.spinner("Loading..."):
    data = get_dashboard_data()
df = data["index"]

st.markdown("<h2 style='color:#E8EAF0'>💡 Innovation Ecosystem</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#9BA3B8'>Startup density, DPIIT-recognized companies, and digital literacy reach.</p>", unsafe_allow_html=True)
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    total_startups = int(df["recognized_startups"].sum())
    st.metric("Total DPIIT Startups", f"{total_startups:,}")
with k2:
    top_startup_state = df.loc[df["recognized_startups"].idxmax(), "state_name"]
    top_count = int(df["recognized_startups"].max())
    st.metric("Startup Capital", top_startup_state, f"{top_count:,} startups")
with k3:
    avg_per_m = df["startups_per_million"].mean()
    st.metric("Avg Startups/Million", f"{avg_per_m:.1f}")
with k4:
    total_digi = int(df["beneficiaries_trained"].sum())
    st.metric("PMGDISHA Beneficiaries", f"{total_digi/1e6:.1f}M")

st.divider()

# ── Startup Ranking ───────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>Startup Density (per million population)</p>", unsafe_allow_html=True)
st.caption("Per-capita normalisation is essential — Maharashtra has more startups than Kerala, but less per million people.")
st.plotly_chart(
    plot_state_ranking(
        df, score_col="startups_per_million",
        color_col="cluster_label",
        title="DPIIT-Recognized Startups per Million Population",
        height=660,
    ),
    use_container_width=True,
)

# ── Talent vs Startups ────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Talent vs Startup Output</p>", unsafe_allow_html=True)
st.caption("States above the trend line convert education into startups efficiently. States below have untapped talent.")

plot_df = df.copy()
for col in ["aicte_institutes_per_million", "startups_per_million", "ai_readiness_score"]:
    plot_df[col] = plot_df[col].astype("float64")

fig_ts = px.scatter(
    plot_df,
    x="aicte_institutes_per_million",
    y="startups_per_million",
    text="state_name",
    color="cluster_label",
    size="ai_readiness_score",
    color_discrete_map={
        "AI Leaders": "#1a9850",
        "Fast Challengers": "#91cf60",
        "Emerging Markets": "#fee08b",
        "Lagging Regions": "#d73027",
    },
    trendline="ols",
    trendline_color_override="#9BA3B8",
    title="AICTE Institutes per Million vs Startups per Million",
    labels={
        "aicte_institutes_per_million": "AICTE Institutes per Million",
        "startups_per_million": "Startups per Million",
        "cluster_label": "Cluster",
    },
    height=500,
)
fig_ts.update_traces(
    textposition="top center",
    textfont=dict(size=8, color=THEME["subtext_color"]),
    selector=dict(mode="markers+text"),
)
fig_ts.update_layout(
    paper_bgcolor=THEME["paper_color"],
    plot_bgcolor=THEME["bg_color"],
    font=dict(color=THEME["text_color"]),
    xaxis=dict(**_styled_axis()),
    yaxis=dict(**_styled_axis()),
)
st.plotly_chart(fig_ts, use_container_width=True)

# ── Talent-without-startups detection ─────────────────────────────────────────
edu_median = df["score_education"].median()
inno_median = df["score_innovation"].median()
talent_gap = df[
    (df["score_education"] >= edu_median) &
    (df["score_innovation"] < inno_median)
][["state_name", "score_education", "score_innovation", "cluster_label"]].copy()
talent_gap = talent_gap.sort_values("score_education", ascending=False)

if not talent_gap.empty:
    st.markdown(
        f"<div class='insight-box'>"
        f"<b>⚠️ Talent without startup output:</b> "
        f"{len(talent_gap)} state(s) score above the national median on Education "
        f"but below median on Innovation — "
        f"<b>{', '.join(talent_gap['state_name'].head(5).tolist())}</b>. "
        f"These states have the human capital for an AI ecosystem but lack the "
        f"entrepreneurial infrastructure to convert it."
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Digital Literacy ──────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.markdown("<p class='section-header'>Digital Literacy Reach (PMGDISHA)</p>", unsafe_allow_html=True)
    st.caption("Beneficiaries per million population — proxy for rural digital literacy program reach.")
    st.plotly_chart(
        plot_state_ranking(
            df,
            score_col="digital_literacy_beneficiaries_per_million",
            color_col="cluster_label",
            title="PMGDISHA Beneficiaries per Million",
            height=500,
        ),
        use_container_width=True,
    )

with c2:
    st.markdown("<p class='section-header'>Innovation Score Distribution</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_distribution(df, "score_innovation",
                          title="Innovation Score — National Distribution"),
        use_container_width=True,
    )
    st.markdown("<p class='section-header'>Key Insight</p>", unsafe_allow_html=True)
    skew = df["score_innovation"].skew()
    st.markdown(
        f"<div class='insight-box'>"
        f"The innovation score distribution is <b>right-skewed (skew = {skew:.2f})</b>. "
        f"A small number of states dominate startup activity while the majority lag significantly. "
        f"This is the classic power-law distribution seen in global startup ecosystems — "
        f"innovation concentrates geographically before diffusing."
        f"</div>",
        unsafe_allow_html=True,
    )
