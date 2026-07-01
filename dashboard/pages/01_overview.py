"""
Page 1 — Overall AI Readiness
==============================
Business question: Which Indian states are best prepared for the AI economy?

Charts on this page
-------------------
- 4 KPI metrics (national summary)
- Full state ranking bar chart (all 36 states)
- Top 5 / Bottom 5 comparison
- Pillar heatmap (states × pillars)
- Cluster scatter plot
- Bubble map
"""

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard.data_loader import get_dashboard_data
from src.visualization.charts import (
    plot_state_ranking,
    plot_pillar_heatmap,
    plot_top_bottom,
    plot_cluster_scatter,
    plot_kpi_indicator,
)
from src.visualization.maps import plot_bubble_map

st.set_page_config(page_title="Overview | India AI Readiness", layout="wide", page_icon="📊")

# ── Global CSS (duplicated so each page is self-contained) ────────────────────
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

# ── Load Data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading pipeline data..."):
    data = get_dashboard_data()

df = data["index"]
weights = data["entropy_weights"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("<h2 style='color:#E8EAF0'>📊 Overall AI Readiness</h2>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#9BA3B8'>National ranking of all 36 states and UTs on the composite AI Readiness Index.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── KPI Row ───────────────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>National Summary</p>", unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

top_state = df.loc[df["ai_readiness_score_rank"] == 1, "state_name"].iloc[0]
top_score = df["ai_readiness_score"].max()
nat_avg = df["ai_readiness_score"].mean()
leaders_count = (df["cluster_label"] == "AI Leaders").sum()

with k1:
    st.metric("🏆 Top State", top_state, f"{top_score:.1f}/100")
with k2:
    st.metric("📈 National Average", f"{nat_avg:.1f}/100", "AI Readiness Score")
with k3:
    st.metric("🌟 AI Leaders", f"{leaders_count} states", "Score > 70")
with k4:
    laggards = (df["cluster_label"] == "Lagging Regions").sum()
    st.metric("⚠️ Lagging Regions", f"{laggards} states", "Score < 25")

st.divider()

# ── Entropy Weights ───────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>Index Methodology — Entropy Weights</p>", unsafe_allow_html=True)

from config.config_loader import get_config
cfg = get_config()

w_cols = st.columns(len(weights))
for col, (pillar, w) in zip(w_cols, sorted(weights.items(), key=lambda x: -x[1])):
    label = cfg["pillars"][pillar]["label"]
    with col:
        st.metric(label, f"{w*100:.1f}%", "weight")

st.markdown(
    "<div class='insight-box'>Weights are computed via <b>entropy weighting</b> — pillars that "
    "discriminate more strongly between states receive higher weight. Infrastructure receives "
    "the lowest weight because near-universal electrification means it no longer separates "
    "states meaningfully.</div>",
    unsafe_allow_html=True,
)
st.divider()

# ── Full State Ranking ────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>All States Ranked</p>", unsafe_allow_html=True)
st.plotly_chart(
    plot_state_ranking(df, title="AI Readiness Score — All 36 States & UTs"),
    use_container_width=True,
)

# ── Top / Bottom ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Top 5 & Bottom 5</p>", unsafe_allow_html=True)
st.plotly_chart(
    plot_top_bottom(df, n=5, title="Top 5 vs Bottom 5 States"),
    use_container_width=True,
)

# ── Pillar Heatmap ────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Pillar Score Heatmap</p>", unsafe_allow_html=True)
st.caption("Each cell shows a state's normalized score (0 = worst, 1 = best) on that pillar. States sorted by overall AI Readiness Score.")
st.plotly_chart(
    plot_pillar_heatmap(df, title="Pillar Heatmap — All States × All Pillars"),
    use_container_width=True,
)

# ── Cluster Map ───────────────────────────────────────────────────────────────
st.divider()
col_left, col_right = st.columns([1.4, 1], gap="large")

with col_left:
    st.markdown("<p class='section-header'>State Clusters</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_cluster_scatter(
            df,
            x_col="score_internet",
            y_col="score_economy",
            title="State Clusters — Internet vs Economy",
        ),
        use_container_width=True,
    )

with col_right:
    st.markdown("<p class='section-header'>Cluster Composition</p>", unsafe_allow_html=True)
    for cluster in ["AI Leaders", "Fast Challengers", "Emerging Markets", "Lagging Regions"]:
        members = df.loc[df["cluster_label"] == cluster, "state_name"].tolist()
        colors = {"AI Leaders": "#1a9850", "Fast Challengers": "#91cf60",
                  "Emerging Markets": "#fee08b", "Lagging Regions": "#d73027"}
        color = colors.get(cluster, "#9BA3B8")
        mean_score = df.loc[df["cluster_label"] == cluster, "ai_readiness_score"].mean()
        st.markdown(
            f"<div class='insight-box' style='border-left-color:{color}'>"
            f"<b style='color:{color}'>{cluster}</b> &nbsp;"
            f"<span style='color:#9BA3B8;font-size:0.8rem'>Avg: {mean_score:.1f} | {len(members)} states</span><br>"
            f"<span style='color:#9BA3B8;font-size:0.8rem'>{', '.join(members[:6])}"
            f"{'...' if len(members) > 6 else ''}</span></div>",
            unsafe_allow_html=True,
        )

# ── Bubble Map ────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Geographic Distribution</p>", unsafe_allow_html=True)
st.plotly_chart(
    plot_bubble_map(df, title="AI Readiness — Geographic Distribution"),
    use_container_width=True,
)
