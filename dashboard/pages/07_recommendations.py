"""
Page 7 — Recommendations
==========================
Business question: What specific actions should policymakers
and investors prioritise based on the index findings?

This page is the consulting deliverable — it synthesises all
previous analysis into actionable, evidence-backed recommendations.
"""

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dashboard.data_loader import get_dashboard_data
from src.visualization.charts import plot_pillar_radar, plot_cluster_scatter

st.set_page_config(page_title="Recommendations | India AI Readiness", layout="wide", page_icon="🧭")
st.markdown("""<style>
    .stApp{background-color:#0F1117}
    [data-testid="stSidebar"]{background-color:#1A1D27;border-right:1px solid #2D3040}
    [data-testid="stMetric"]{background-color:#1A1D27;border:1px solid #2D3040;border-radius:8px;padding:16px}
    [data-testid="stMetricValue"]{color:#00BCD4}
    .insight-box{background-color:#1A1D27;border-left:3px solid #00BCD4;border-radius:4px;padding:12px 16px;margin:8px 0;color:#E8EAF0;font-size:.9rem;line-height:1.6}
    .rec-card{background-color:#1A1D27;border:1px solid #2D3040;border-radius:10px;padding:20px;margin:10px 0}
    .section-header{color:#00BCD4;font-size:.75rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px;margin-top:24px}
    .opp-card{background-color:#1A1D27;border-left:4px solid #fee08b;border-radius:4px;padding:16px;margin:8px 0}
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    .stPlotlyChart{border:1px solid #2D3040;border-radius:8px}
</style>""", unsafe_allow_html=True)

with st.spinner("Loading..."):
    data = get_dashboard_data()
df = data["index"]
opp_df = data["opportunity"]
corr_insights = data["corr_results"].get("insights", [])

st.markdown("<h2 style='color:#E8EAF0'>🧭 Recommendations</h2>", unsafe_allow_html=True)
st.markdown(
    "<p style='color:#9BA3B8'>"
    "Evidence-backed policy and investment recommendations derived from the AI Readiness Index."
    "</p>",
    unsafe_allow_html=True,
)
st.divider()

# ── Executive Summary KPIs ────────────────────────────────────────────────────
st.markdown("<p class='section-header'>Index at a Glance</p>", unsafe_allow_html=True)
k1, k2, k3, k4, k5 = st.columns(5)

from config.config_loader import get_config
cfg = get_config()
weights = data["entropy_weights"]
top_pillar = max(weights, key=weights.get)
top_pillar_label = cfg["pillars"][top_pillar]["label"]

with k1:
    st.metric("States Analysed", "36", "States + UTs")
with k2:
    st.metric("Pillars", "5", "Dimensions")
with k3:
    st.metric("Top Pillar Weight", f"{weights[top_pillar]*100:.1f}%", top_pillar_label)
with k4:
    st.metric("Sensitivity (Spearman)", "0.996", "Entropy vs Equal")
with k5:
    st.metric("Opportunity States", str(len(opp_df)), "Latent Potential")

st.divider()

# ── Tier-Based Recommendations ────────────────────────────────────────────────
st.markdown("<p class='section-header'>Recommendations by Cluster</p>", unsafe_allow_html=True)

cluster_recs = [
    {
        "cluster": "AI Leaders",
        "color": "#1a9850",
        "icon": "🥇",
        "states": df[df["cluster_label"] == "AI Leaders"]["state_name"].tolist(),
        "score": df[df["cluster_label"] == "AI Leaders"]["ai_readiness_score"].mean(),
        "finding": "High across all pillars. Innovation is the relative bottleneck.",
        "recommendations": [
            "Establish state-level AI regulatory sandboxes to accelerate responsible AI deployment.",
            "Attract global AI R&D centres by offering IP protection and talent incentives.",
            "Build on existing infrastructure advantage to host national AI compute clusters.",
            "Focus startup policy on deep-tech and AI-native ventures rather than broad startup counts.",
        ],
    },
    {
        "cluster": "Fast Challengers",
        "color": "#91cf60",
        "icon": "📈",
        "states": df[df["cluster_label"] == "Fast Challengers"]["state_name"].tolist()[:6],
        "states_suffix": f"+ {max(0, len(df[df['cluster_label'] == 'Fast Challengers']) - 6)} more",
        "score": df[df["cluster_label"] == "Fast Challengers"]["ai_readiness_score"].mean(),
        "finding": "Strong internet and infrastructure. Innovation conversion is the gap.",
        "recommendations": [
            "Invest in startup incubator density — strong AICTE presence is not converting to ventures.",
            "Partner with central government PM GatiShakti nodes to upgrade last-mile connectivity.",
            "Create state AI talent retention schemes: brain drain to metros suppresses local innovation.",
            "Prioritise female digital literacy programmes to expand the addressable talent pool.",
        ],
    },
    {
        "cluster": "Emerging Markets",
        "color": "#fee08b",
        "icon": "🌱",
        "states": df[df["cluster_label"] == "Emerging Markets"]["state_name"].tolist(),
        "score": df[df["cluster_label"] == "Emerging Markets"]["ai_readiness_score"].mean(),
        "finding": "Surprise innovation scores — but economy and internet hold them back.",
        "recommendations": [
            "Northeast states show disproportionate innovation output relative to their size — "
            "targeted BharatNet expansion could unlock significant digital upside.",
            "Leverage existing startup activity to attract VC attention via state showcases.",
            "Prioritise GSDP growth policy: economic development is the highest-weight predictor.",
            "Invest in cross-state connectivity with fast challengers to enable talent mobility.",
        ],
    },
    {
        "cluster": "Lagging Regions",
        "color": "#d73027",
        "icon": "⚠️",
        "states": df[df["cluster_label"] == "Lagging Regions"]["state_name"].tolist()[:6],
        "states_suffix": f"+ {max(0, len(df[df['cluster_label'] == 'Lagging Regions']) - 6)} more",
        "score": df[df["cluster_label"] == "Lagging Regions"]["ai_readiness_score"].mean(),
        "finding": "Structural gaps across multiple pillars. Foundational investment needed first.",
        "recommendations": [
            "Internet first: AI readiness is impossible without baseline connectivity. "
            "Prioritise BharatNet Phase 2 in UP, Bihar, Jharkhand, and Assam.",
            "Literacy is the foundation — PM eVidya and digital literacy programmes should "
            "scale in these states before AI-specific investments.",
            "Economic development drives AI readiness more than any single pillar (ρ = 0.91). "
            "MSME digitisation schemes offer the highest multiplier for these states.",
            "These states should not be excluded from national AI policy — they represent "
            "60%+ of India's population and the AI economy's future mass market.",
        ],
    },
]

for rec in cluster_recs:
    states_str = ", ".join(rec["states"])
    if "states_suffix" in rec:
        states_str += f" {rec['states_suffix']}"

    st.markdown(
        f"<div class='rec-card'>"
        f"<h3 style='color:{rec['color']};margin-top:0'>"
        f"{rec['icon']} {rec['cluster']} — Avg Score: {rec['score']:.1f}/100</h3>"
        f"<p style='color:#9BA3B8;font-size:0.82rem;margin-bottom:8px'>{states_str}</p>"
        f"<p style='color:#E8EAF0;font-size:0.9rem'><b>Finding:</b> {rec['finding']}</p>"
        f"<ul style='color:#E8EAF0;font-size:0.88rem;line-height:1.8;margin-top:8px'>",
        unsafe_allow_html=True,
    )
    for r in rec["recommendations"]:
        st.markdown(f"<li>{r}</li>", unsafe_allow_html=True)
    st.markdown("</ul></div>", unsafe_allow_html=True)

# ── Opportunity States ─────────────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Opportunity States — Latent Potential</p>", unsafe_allow_html=True)
st.caption("These states score below the national median overall, but lead nationally on at least one pillar. "
           "A single targeted intervention could unlock disproportionate AI readiness gains.")

if opp_df.empty:
    st.info("No opportunity states identified at current thresholds.")
else:
    for _, opp_row in opp_df.iterrows():
        st.markdown(
            f"<div class='opp-card'>"
            f"<b style='color:#fee08b'>{opp_row['state_name']}</b> "
            f"<span style='color:#9BA3B8;font-size:0.8rem'>Rank #{int(opp_row['ai_readiness_score_rank'])} | "
            f"Score: {opp_row['ai_readiness_score']:.1f}</span><br>"
            f"<span style='color:#E8EAF0;font-size:0.88rem'>"
            f"Strength: <b>{opp_row['strongest_pillar']}</b> · "
            f"Bottleneck: <b>{opp_row['weakest_pillar']}</b></span><br>"
            f"<span style='color:#9BA3B8;font-size:0.84rem;line-height:1.6'>"
            f"{opp_row.get('state_narrative', '')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Correlation-Driven Recommendations ────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>Investment Leverage Points</p>", unsafe_allow_html=True)
st.caption("Derived from Spearman correlation analysis — where does one investment generate multiple pillar gains?")

leverage_insights = [
    ("Internet Infrastructure", "0.77 correlation with Infrastructure pillar",
     "Broadband investment simultaneously improves both internet readiness AND physical infrastructure scores. "
     "It is the highest-leverage single investment in the AI readiness framework."),
    ("Economic Development", "0.91 correlation with AI Readiness Score",
     "GSDP per capita is the single strongest predictor of overall AI readiness. "
     "MSME digitisation, GST compliance improvements, and industrial policy have the "
     "highest multiplier on AI readiness across all states."),
    ("Education → Innovation Pipeline", "0.74 Education × Innovation correlation",
     "States with strong education systems tend to have stronger innovation ecosystems. "
     "The causal direction suggests education investment precedes startup creation by ~5–10 years. "
     "States investing in AICTE capacity today are building their 2030 innovation base."),
]

for title, stat, desc in leverage_insights:
    st.markdown(
        f"<div class='insight-box'>"
        f"<b>{title}</b> <span style='color:#9BA3B8;font-size:0.8rem'>({stat})</span><br>"
        f"{desc}"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── State Narrative Explorer ──────────────────────────────────────────────────
st.divider()
st.markdown("<p class='section-header'>All State Narratives</p>", unsafe_allow_html=True)
st.caption("Click any state to read its AI readiness narrative.")

all_states = df.sort_values("ai_readiness_score_rank")["state_name"].tolist()
selected = st.selectbox("Select state", all_states, key="rec_state_select")

if selected:
    row = df[df["state_name"] == selected].iloc[0]
    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.markdown(
            f"<div class='insight-box' style='font-size:0.92rem;line-height:1.8'>"
            f"{row.get('state_narrative', 'Narrative not available.')}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.plotly_chart(
            plot_pillar_radar(df, [selected], title=f"{selected} — Pillar Profile"),
            use_container_width=True,
        )

# ── Methodology Footer ────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<p style='color:#9BA3B8;font-size:0.78rem;line-height:1.8'>"
    "<b>Methodology:</b> AI Readiness Index uses entropy weighting (OECD Handbook on Composite Indicators, 2008). "
    "Sensitivity analysis confirms Spearman rank correlation of 0.996 between entropy-weighted "
    "and equal-weighted rankings, validating robustness. "
    "Data sources: TRAI (internet/broadband), AICTE (institutes), Census 2011 + NFHS-5 (literacy), "
    "CEA (electricity), DPIIT (startups), MoSPI/RBI (GDP), PMGDISHA (digital literacy). "
    "Data vintage: 2021–2023."
    "</p>",
    unsafe_allow_html=True,
)
