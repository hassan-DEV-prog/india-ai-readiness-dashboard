"""
Page 6 — Gap Analysis
======================
Business question: For any given state, which pillar is the
single biggest barrier to AI readiness improvement?
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
    plot_gap_bar, plot_pillar_radar, plot_correlation_heatmap,
    THEME, _base_layout, _styled_axis,
)

st.set_page_config(page_title="Gap Analysis | India AI Readiness", layout="wide", page_icon="🔍")
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
corr_results = data["corr_results"]

st.markdown("<h2 style='color:#E8EAF0'>🔍 Gap Analysis</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#9BA3B8'>Identify the specific pillar holding each state back from higher AI readiness.</p>", unsafe_allow_html=True)
st.divider()

# ── State Selector ────────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>State Deep-Dive</p>", unsafe_allow_html=True)

all_states = df.sort_values("ai_readiness_score_rank")["state_name"].tolist()
selected_state = st.selectbox(
    "Select a state to analyse",
    options=all_states,
    index=0,
    key="gap_state_select",
)

row = df[df["state_name"] == selected_state].iloc[0]

# State summary header
rank = int(row["ai_readiness_score_rank"])
score = float(row["ai_readiness_score"])
cluster = row["cluster_label"]
strongest = row.get("strongest_pillar", "—")
weakest = row.get("weakest_pillar", "—")

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.metric("National Rank", f"#{rank}", f"of 36 states")
with col_b:
    st.metric("AI Readiness Score", f"{score:.1f}/100")
with col_c:
    st.metric("Cluster", cluster)
with col_d:
    st.metric("Weakest Pillar", weakest)

st.divider()

# ── Gap Bar + Radar Side by Side ──────────────────────────────────────────────
left, right = st.columns(2, gap="large")

with left:
    st.markdown("<p class='section-header'>Pillar Breakdown</p>", unsafe_allow_html=True)
    st.caption("Bars above the dashed line are above this state's own average; below = bottleneck.")
    st.plotly_chart(
        plot_gap_bar(df, selected_state, height=380),
        use_container_width=True,
    )

with right:
    st.markdown("<p class='section-header'>Radar vs Cluster Peers</p>", unsafe_allow_html=True)
    # Show selected state + cluster average state (best in same cluster)
    cluster_peers = df[df["cluster_label"] == cluster].sort_values("ai_readiness_score", ascending=False)
    peer_top = cluster_peers.iloc[0]["state_name"] if len(cluster_peers) > 1 else selected_state
    compare_states = list(dict.fromkeys([selected_state, peer_top]))

    st.plotly_chart(
        plot_pillar_radar(df, compare_states,
                          title=f"{selected_state} vs {peer_top} (top cluster peer)"),
        use_container_width=True,
    )

# ── Narrative ─────────────────────────────────────────────────────────────────
narrative = row.get("state_narrative", "")
if narrative:
    st.markdown(
        f"<div class='insight-box' style='font-size:0.92rem;line-height:1.8'>{narrative}</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── National Weakest Pillar Summary ──────────────────────────────────────────
st.markdown("<p class='section-header'>National Bottleneck Map</p>", unsafe_allow_html=True)
st.caption("For each state, which pillar is the single biggest drag? This shows where national AI policy should focus.")

if "weakest_pillar" in df.columns:
    bottleneck_counts = df["weakest_pillar"].value_counts().reset_index()
    bottleneck_counts.columns = ["Pillar", "Number of States"]

    fig_bn = go.Figure(go.Bar(
        x=bottleneck_counts["Pillar"],
        y=bottleneck_counts["Number of States"],
        marker_color=[THEME["negative"], THEME["accent"], THEME["neutral"],
                      THEME["positive"], "#AB47BC"][:len(bottleneck_counts)],
        text=bottleneck_counts["Number of States"],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y} states have this as their weakest pillar<extra></extra>",
    ))
    layout = _base_layout("States' Weakest Pillar (where most states lag behind their own average)", height=360)
    layout.update(
        xaxis=dict(**_styled_axis(), showgrid=False),
        yaxis=dict(**_styled_axis(), title="Number of States"),
        showlegend=False,
    )
    fig_bn.update_layout(**layout)
    st.plotly_chart(fig_bn, use_container_width=True)

    top_bottleneck = bottleneck_counts.iloc[0]
    st.markdown(
        f"<div class='insight-box'>"
        f"<b>{top_bottleneck['Pillar']}</b> is the most common bottleneck — "
        f"{top_bottleneck['Number of States']} states score below their own average here. "
        f"This makes it the highest-leverage policy target for improving national AI readiness."
        f"</div>",
        unsafe_allow_html=True,
    )

# ── Correlation Matrix ────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Pillar Correlation Matrix</p>", unsafe_allow_html=True)
st.caption("Understanding which pillars move together helps identify where targeted investment has spillover effects.")
st.plotly_chart(
    plot_correlation_heatmap(
        corr_results["spearman_matrix"],
        title="Spearman Rank Correlation — Pillar Scores",
    ),
    use_container_width=True,
)

# ── Correlation Insights ──────────────────────────────────────────────────────
st.markdown("<p class='section-header'>Correlation Insights</p>", unsafe_allow_html=True)
for insight in corr_results.get("insights", []):
    st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)
