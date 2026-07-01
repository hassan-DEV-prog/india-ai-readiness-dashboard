"""
India AI Readiness Dashboard
============================
Streamlit multi-page application entry point.

Run locally:
    streamlit run dashboard/app.py

Deploy:
    Push to GitHub → connect Streamlit Cloud → public URL auto-generated.

Page Structure
--------------
This file configures global settings and renders the landing page.
Individual pages live in dashboard/pages/ and are auto-discovered
by Streamlit's multi-page app system.
"""

import sys
from pathlib import Path

import streamlit as st

# ── Path Setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Page Config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="India AI Readiness Dashboard",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/hassan-DEV-prog/india-ai-readiness-dashboard",
        "Report a bug": "https://github.com/hassan-DEV-prog/india-ai-readiness-dashboard/issues",
        "About": "India AI Readiness Dashboard v1.0 — Measuring AI readiness across 36 Indian states.",
    },
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0F1117; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1A1D27;
        border-right: 1px solid #2D3040;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #1A1D27;
        border: 1px solid #2D3040;
        border-radius: 8px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { color: #00BCD4; font-size: 2rem; }
    [data-testid="stMetricLabel"] { color: #9BA3B8; font-size: 0.85rem; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }

    /* Insight boxes */
    .insight-box {
        background-color: #1A1D27;
        border-left: 3px solid #00BCD4;
        border-radius: 4px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #E8EAF0;
        font-size: 0.9rem;
        line-height: 1.6;
    }

    /* Section headers */
    .section-header {
        color: #00BCD4;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 12px;
        margin-top: 24px;
    }

    /* Narrative card */
    .narrative-card {
        background-color: #1A1D27;
        border: 1px solid #2D3040;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        color: #E8EAF0;
        font-size: 0.88rem;
        line-height: 1.7;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Plotly chart borders */
    .stPlotlyChart {
        border: 1px solid #2D3040;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🇮🇳 India AI Readiness")
    st.markdown(
        "<span style='color:#9BA3B8;font-size:0.8rem;'>"
        "Measuring AI readiness across 36 states & UTs"
        "</span>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        "<span style='color:#9BA3B8;font-size:0.75rem;'>"
        "Data sources: TRAI · AICTE · Census · CEA · DPIIT · MoSPI<br>"
        "Methodology: Entropy Weighting (OECD Handbook)<br>"
        "Last updated: 2023–24"
        "</span>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        "<span style='color:#9BA3B8;font-size:0.75rem;'>"
        "Built with Python · Streamlit · Plotly<br>"
        "[GitHub ↗](https://github.com/hassan-DEV-prog/india-ai-readiness-dashboard)"
        "</span>",
        unsafe_allow_html=True,
    )

# ── Landing Page ──────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#E8EAF0;font-size:2rem;margin-bottom:0'>India AI Readiness Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#9BA3B8;font-size:1rem;margin-top:4px'>"
    "Which Indian states are best prepared for the AI economy?</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── How to Navigate ───────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown("### What this dashboard measures")
    st.markdown("""
A composite **AI Readiness Index** built from 5 pillars across 36 Indian states and Union Territories.
Each pillar is normalized to [0,1] using Min-Max scaling.
Pillar weights are determined by **entropy weighting** — a data-driven methodology from the
[OECD Handbook on Composite Indicators](https://www.oecd.org/sdd/42495745.pdf) —
ensuring that pillars which most discriminate between states receive higher weight.
    """)

    st.markdown("### The 5 Pillars")

    from dashboard.data_loader import get_dashboard_data
    from config.config_loader import get_config
    _data = get_dashboard_data()
    _df   = _data["index"]
    _w    = _data["entropy_weights"]

    pillars = [
        ("🌐", "internet",      "Internet Readiness",    "Penetration, broadband density, rural connectivity",
         ["internet_penetration_pct","broadband_subscribers_per_100","rural_internet_pct"],
         ["Internet Penetration %","Broadband per 100","Rural Internet %"]),
        ("🎓", "education",     "Education & Talent",    "Literacy, AICTE institutes, engineering capacity",
         ["literacy_rate_pct","aicte_institutes_per_million","engineering_seats_per_million"],
         ["Literacy Rate %","AICTE Institutes /M","Engg Seats /M"]),
        ("⚡", "infrastructure","Infrastructure",         "Electrification, per-capita consumption",
         ["electrification_pct","per_capita_power_consumption_kwh"],
         ["Electrification %","Power kWh /capita"]),
        ("💡", "innovation",    "Innovation Ecosystem",  "Startup density, digital literacy reach",
         ["startups_per_million","digital_literacy_beneficiaries_per_million"],
         ["Startups /M","PMGDISHA /M"]),
        ("💰", "economy",       "Economic Strength",     "GSDP per capita, urbanization",
         ["gsdp_per_capita_inr","urbanization_pct"],
         ["GSDP per Capita ₹","Urbanization %"]),
    ]

    for icon, key, name, desc, cols, labels in pillars:
        weight_pct = round(_w.get(key, 0) * 100, 1)
        with st.expander(f"{icon} **{name}** — weight {weight_pct}%"):
            st.caption(desc)
            st.divider()
            score_col = f"score_{key}"
            if score_col in _df.columns:
                top3 = _df.nlargest(3, score_col)[["state_name", score_col]]
                bot3 = _df.nsmallest(3, score_col)[["state_name", score_col]]
                t_col, b_col = st.columns(2)
                with t_col:
                    st.markdown("**🏆 Top 3**")
                    for _, row in top3.iterrows():
                        st.markdown(f"<span style='color:#1a9850'>●</span> **{row['state_name']}** — {row[score_col]:.2f}", unsafe_allow_html=True)
                with b_col:
                    st.markdown("**⚠️ Bottom 3**")
                    for _, row in bot3.iterrows():
                        st.markdown(f"<span style='color:#d73027'>●</span> **{row['state_name']}** — {row[score_col]:.2f}", unsafe_allow_html=True)
            st.divider()
            st.markdown("**National averages**")
            metric_cols = st.columns(len(cols))
            for mc, col, label in zip(metric_cols, cols, labels):
                if col in _df.columns:
                    with mc:
                        st.metric(label, f"{_df[col].mean():,.1f}")

with col2:
    st.markdown("### Dashboard pages")
    pages = [
        ("📊", "01 Overview", "National rankings, top/bottom states, cluster map"),
        ("🌐", "02 Internet", "Broadband growth, rural vs urban, penetration heatmap"),
        ("🎓", "03 Education", "Literacy rates, technical institutes, talent density"),
        ("💡", "04 Innovation", "Startup density, digital literacy, ecosystem analysis"),
        ("⚡", "05 Infrastructure", "Electricity, power consumption, state comparison"),
        ("🔍", "06 Gap Analysis", "Pillar gaps, bottleneck identification, peer comparison"),
        ("🧭", "07 Recommendations", "Insight narratives, opportunity states, policy levers"),
    ]
    for icon, name, desc in pages:
        st.markdown(
            f"<div class='narrative-card'>"
            f"<b style='color:#00BCD4'>{icon} {name}</b><br>"
            f"<span style='color:#9BA3B8;font-size:0.82rem;'>{desc}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("### Methodology note")
    st.info(
        "Sensitivity analysis confirms Spearman rank correlation of **0.996** "
        "between entropy-weighted and equal-weighted rankings, validating that "
        "the index is robust to weighting method choice.",
        icon="ℹ️",
    )

st.divider()
st.markdown(
    "<p style='color:#9BA3B8;font-size:0.75rem;text-align:center;'>"
    "Navigate using the sidebar pages → | "
    "Data vintage: 2021–2023 | "
    "Index methodology: Entropy Weighting (OECD 2008)"
    "</p>",
    unsafe_allow_html=True,
)
