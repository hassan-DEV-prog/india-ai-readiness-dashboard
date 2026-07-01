"""
Page 3 — Education & Talent
============================
Business question: Which states have the human capital foundations
for an AI economy — and where are the talent gaps?
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
    plot_state_ranking, plot_distribution, plot_pillar_radar,
    THEME, _base_layout, _styled_axis,
)

st.set_page_config(page_title="Education | India AI Readiness", layout="wide", page_icon="🎓")
st.markdown("""<style>
    .stApp{background-color:#0F1117}
    [data-testid="stSidebar"]{background-color:#1A1D27;border-right:1px solid #2D3040}
    [data-testid="stMetric"]{background-color:#1A1D27;border:1px solid #2D3040;border-radius:8px;padding:16px}
    [data-testid="stMetricValue"]{color:#00BCD4}
    .insight-box{background-color:#1A1D27;border-left:3px solid #4CAF50;border-radius:4px;padding:12px 16px;margin:8px 0;color:#E8EAF0;font-size:.9rem;line-height:1.6}
    .section-header{color:#4CAF50;font-size:.75rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px;margin-top:24px}
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    .stPlotlyChart{border:1px solid #2D3040;border-radius:8px}
</style>""", unsafe_allow_html=True)

with st.spinner("Loading..."):
    data = get_dashboard_data()
df = data["index"]

st.markdown("<h2 style='color:#E8EAF0'>🎓 Education & Talent</h2>", unsafe_allow_html=True)
st.markdown("<p style='color:#9BA3B8'>Literacy rates, technical institute density, and the human capital pipeline for AI.</p>", unsafe_allow_html=True)
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Avg Literacy Rate", f"{df['literacy_rate_pct'].mean():.1f}%")
with k2:
    top_lit = df.loc[df["literacy_rate_pct"].idxmax(), "state_name"]
    st.metric("Highest Literacy", top_lit, f"{df['literacy_rate_pct'].max():.1f}%")
with k3:
    st.metric("Avg AICTE Institutes/M", f"{df['aicte_institutes_per_million'].mean():.1f}")
with k4:
    gender_gap = (df["male_literacy_pct"] - df["female_literacy_pct"]).mean()
    st.metric("Avg Gender Literacy Gap", f"{gender_gap:.1f} pp", "Male minus Female")

st.divider()

# ── Literacy Ranking ──────────────────────────────────────────────────────────
st.markdown("<p class='section-header'>Overall Literacy Rate by State</p>", unsafe_allow_html=True)
st.plotly_chart(
    plot_state_ranking(
        df, score_col="literacy_rate_pct",
        color_col="cluster_label",
        title="Literacy Rate (%) — All States",
        height=660,
    ),
    use_container_width=True,
)

# ── Gender Gap ────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Gender Literacy Gap</p>", unsafe_allow_html=True)
st.caption("The male–female literacy gap is a structural AI readiness barrier: female digital exclusion constrains the overall talent pool.")

gender_df = df[["state_name", "male_literacy_pct", "female_literacy_pct"]].copy()
gender_df["gap"] = gender_df["male_literacy_pct"] - gender_df["female_literacy_pct"]
gender_df = gender_df.sort_values("gap", ascending=True)

fig_g = go.Figure()
fig_g.add_trace(go.Bar(
    y=gender_df["state_name"],
    x=gender_df["gap"],
    orientation="h",
    marker=dict(
        color=gender_df["gap"],
        colorscale=[[0, "#1a9850"], [0.5, "#fee08b"], [1, "#d73027"]],
        showscale=False,
    ),
    text=gender_df["gap"].round(1).astype(str) + " pp",
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>Gap: %{x:.1f} pp<extra></extra>",
))
layout = _base_layout("Male–Female Literacy Gap (percentage points)", height=660)
layout.update(
    xaxis=dict(**_styled_axis(), title="Gap (pp)", showgrid=True),
    yaxis=dict(**_styled_axis(), showgrid=False),
    showlegend=False,
)
fig_g.add_vline(x=gender_df["gap"].mean(), line_dash="dash",
                line_color=THEME["neutral"], line_width=1.5,
                annotation_text=f"Mean: {gender_df['gap'].mean():.1f} pp",
                annotation_font=dict(color=THEME["neutral"], size=10))
fig_g.update_layout(**layout)
st.plotly_chart(fig_g, use_container_width=True)

# ── AICTE Institutes ──────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)

with c1:
    st.markdown("<p class='section-header'>AICTE Institutes per Million Population</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_state_ranking(
            df, score_col="aicte_institutes_per_million",
            color_col="cluster_label",
            title="Technical Institutes per Million",
            height=500,
        ),
        use_container_width=True,
    )

with c2:
    st.markdown("<p class='section-header'>Engineering Seats per Million</p>", unsafe_allow_html=True)
    st.plotly_chart(
        plot_state_ranking(
            df, score_col="engineering_seats_per_million",
            color_col="cluster_label",
            title="Engineering Seats per Million",
            height=500,
        ),
        use_container_width=True,
    )

# ── Radar Comparison ──────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Pillar Radar — Compare States</p>", unsafe_allow_html=True)
st.caption("Select up to 3 states to compare their full pillar profile.")

all_states = sorted(df["state_name"].tolist())
selected = st.multiselect(
    "Select states to compare",
    options=all_states,
    default=["Kerala", "Bihar", "Karnataka"],
    max_selections=3,
    key="edu_radar_select",
)

if selected:
    st.plotly_chart(
        plot_pillar_radar(df, selected, title=f"Pillar Radar — {', '.join(selected)}"),
        use_container_width=True,
    )

# ── Insights ──────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Key Education Insights</p>", unsafe_allow_html=True)

insights = [
    f"Kerala leads all states with a {df.loc[df['literacy_rate_pct'].idxmax(), 'literacy_rate_pct']:.1f}% "
    f"literacy rate, but ranks only 11th overall — constrained by a weak innovation ecosystem.",

    f"The average gender literacy gap of {gender_gap:.1f} percentage points represents "
    f"a structural barrier: AI talent pools require female participation to reach full depth.",

    f"Maharashtra and Tamil Nadu dominate on raw AICTE institute count, but smaller states "
    f"like Chandigarh and Himachal Pradesh lead on institutes per million — suggesting better "
    f"per-capita access to technical education.",
]

for insight in insights:
    st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)
