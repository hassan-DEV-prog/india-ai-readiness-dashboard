# 🇮🇳 India AI Readiness Dashboard

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-5.22-3F4F75?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000?style=flat-square)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

> **Which Indian states are best prepared for the AI economy?**
>
> A production-quality analytics project measuring AI readiness across all 36 Indian states and Union Territories using a composite index built from 9 public datasets across 5 structural pillars.

🔗 **[Live Dashboard →](https://india-ai-readiness.streamlit.app)**
&nbsp;|&nbsp;
📊 **[Power BI Report →](dashboard/AI_Readiness.pbix)**
&nbsp;|&nbsp;
📖 **[Methodology →](docs/methodology.md)**

---

## What This Project Does

Rather than listing raw statistics, this dashboard builds a **defensible composite index** — the **India AI Readiness Score** — that ranks every Indian state on their structural preparedness for an AI-driven economy.

The index is built with the same rigor used by UNDP, World Bank, and OECD index methodologies:

- **Data-driven weights** via entropy weighting (no arbitrary percentages)
- **Sensitivity validation** via Spearman rank correlation between weighting methods (ρ = 0.996)
- **Transparent imputation** with regional median and explicit imputation flags
- **Honest proxy documentation** for datasets without direct measures

### Key Findings

| Rank | State | Score | Cluster |
|------|-------|-------|---------|
| 1 | Chandigarh | 83.5 | AI Leaders |
| 2 | Goa | 76.4 | AI Leaders |
| 3 | NCT of Delhi | 65.2 | Fast Challengers |
| 4 | Haryana | 64.1 | AI Leaders |
| 5 | Puducherry | 61.1 | Fast Challengers |
| … | … | … | … |
| 36 | Bihar | 9.96 | Lagging Regions |

**Economy** is the highest-weight pillar (28.5%) — GSDP per capita is the single strongest predictor of AI readiness. **Infrastructure** receives the lowest weight (13.5%) because near-universal electrification means it no longer discriminates between states — which is analytically correct, not a flaw.

---

## Architecture

```
Raw Data (9 CSVs + TRAI PDFs)
         │
         ▼
   src/etl/loader.py          ← typed loaders, one per source
         │
         ▼
   src/etl/cleaner.py         ← state name standardization, range validation,
         │                       regional median imputation with flags
         ▼
   src/etl/merger.py          ← spine-based left join, per-capita derivations
         │
         ▼
data/processed/states_merged.csv   ◄── also consumed by Power BI
         │
         ▼
src/features/normalizer.py    ← Min-Max normalization, pillar score aggregation
         │
         ▼
src/features/index_builder.py ← entropy weights, composite score, sensitivity check
         │
         ▼
src/analysis/
  clustering.py               ← K-Means (k=4), silhouette-validated
  correlation.py              ← Spearman + Pearson, insight generation
  gap_analysis.py             ← pillar gaps, opportunity states, narratives
         │
         ▼
src/visualization/
  charts.py                   ← 9 reusable Plotly chart functions
  maps.py                     ← choropleth + bubble map, GeoJSON fallback
         │
         ▼
dashboard/
  app.py                      ← Streamlit entry point
  pages/01–07                 ← 7 analytical pages
         │
         ▼
Streamlit Cloud               ← public URL, auto-redeploys on git push
```

---

## Dashboard Pages

| Page | Business Question | Charts |
|------|------------------|--------|
| **01 Overview** | Which states lead and lag overall? | Ranking bar, heatmap, cluster scatter, bubble map |
| **02 Internet** | What is the digital connectivity divide? | Rural vs urban, broadband scatter, distributions |
| **03 Education** | Where is the AI talent pipeline strongest? | Literacy ranking, gender gap, radar comparator |
| **04 Innovation** | Where is startup activity concentrated? | Startup density, talent-vs-startups scatter |
| **05 Infrastructure** | Is physical infrastructure AI-ready? | Power consumption, electrification analysis |
| **06 Gap Analysis** | What single pillar holds each state back? | State deep-dive, national bottleneck map, correlations |
| **07 Recommendations** | What should policymakers prioritise? | Cluster-based recs, opportunity states, narratives |

---

## Index Methodology

### Pillar Structure

| Pillar | Weight | Features |
|--------|--------|----------|
| 🌐 Internet Readiness | **25.3%** | Penetration %, broadband/100, rural internet % |
| 🎓 Education & Talent | **13.0%** | Literacy rate, AICTE institutes/M, eng seats/M |
| ⚡ Infrastructure | **13.5%** | Electrification %, per-capita kWh |
| 💡 Innovation Ecosystem | **19.7%** | Startups/M, PMGDISHA beneficiaries/M |
| 💰 Economic Strength | **28.5%** | GSDP per capita, urbanization % |

### Entropy Weighting — Why This Method

Five methods were compared:

| Method | Pros | Cons | Used? |
|--------|------|------|-------|
| Equal weights | Transparent, simple | Ignores discriminatory power | Sensitivity check ✓ |
| Expert weights | Domain-justified | Arbitrary without real panel | ✗ |
| PCA | Statistically rigorous | Unstable with N=36 | ✗ |
| **Entropy weighting** | **Data-driven, reproducible, works with small N** | Rewards variance, not importance | **Primary ✓** |
| AHP | Pairwise justified | Requires real expert panel | ✗ |

**Entropy weighting** assigns higher weight to pillars that most discriminate between states. A pillar where all states score identically (zero information) receives near-zero weight. The methodology is documented in [OECD (2008), Handbook on Constructing Composite Indicators](https://www.oecd.org/sdd/42495745.pdf), Chapter 6.

### Sensitivity Validation

The Spearman rank correlation between entropy-weighted and equal-weighted rankings is **ρ = 0.996**, with a maximum rank shift of 3 positions. The index is robust to weighting method choice.

### Normalization

All features are normalized using **Min-Max scaling** to [0, 1] with outlier clipping at ±3σ before normalization. The Min-Max method is preferred over Z-score for composite indices because it preserves a bounded [0, 1] range, enabling direct score interpretation.

---

## Data Sources

| Dataset | Source | Format | Vintage |
|---------|--------|--------|---------|
| Internet penetration | TRAI Annual Report | CSV (from PDF) | 2023 |
| Broadband subscribers | TRAI Quarterly Report | CSV (from PDF) | Q3 2023 |
| Literacy rates | Census 2011 + NFHS-5 | CSV | 2011 / 2021 |
| AICTE institutes | AICTE Open Data Portal | CSV | 2023 |
| State GDP (GSDP) | MoSPI / RBI Handbook | CSV | 2022-23 |
| Population | Census 2011 + Projections | CSV | 2023 est. |
| Electricity stats | CEA Annual Report | CSV | 2023 |
| DPIIT startups | Startup India Annual Report | CSV | 2023 |
| Digital literacy | PMGDISHA Programme Reports | CSV | 2023 |
| State boundaries | [GeoJSON — Subhash9325](https://github.com/Subhash9325/GeoJson-Data-of-Indian-States) | GeoJSON | 2019 |

**Proxy disclosure:** PMGDISHA beneficiary count is used as a proxy for digital literacy reach, not true digital literacy rate. This limitation is explicitly documented in [data_dictionary.md](docs/data_dictionary.md).

---

## Project Structure

```
india-ai-readiness-dashboard/
│
├── config/
│   ├── settings.yaml          # Single source of truth — all parameters
│   └── config_loader.py       # LRU-cached YAML loader
│
├── data/
│   ├── raw/                   # Source CSVs (committed), PDFs (git-ignored)
│   ├── processed/             # states_merged.csv + ai_readiness_index.csv
│   └── external/              # india_states.geojson
│
├── src/
│   ├── logger.py              # Rotating file + console logging
│   ├── etl/
│   │   ├── loader.py          # Typed data loaders, one per source
│   │   ├── cleaner.py         # Standardization, validation, imputation
│   │   └── merger.py          # Spine-based joins, per-capita derivations
│   ├── features/
│   │   ├── normalizer.py      # Min-Max with outlier clipping
│   │   └── index_builder.py   # Entropy weights + composite score
│   ├── analysis/
│   │   ├── clustering.py      # K-Means segmentation
│   │   ├── correlation.py     # Spearman/Pearson + insights
│   │   └── gap_analysis.py    # Pillar gaps + state narratives
│   └── visualization/
│       ├── charts.py          # 9 reusable Plotly chart functions
│       └── maps.py            # Choropleth + bubble map
│
├── dashboard/
│   ├── app.py                 # Streamlit entry point
│   ├── data_loader.py         # @st.cache_data pipeline runner
│   └── pages/
│       ├── 01_overview.py
│       ├── 02_internet.py
│       ├── 03_education.py
│       ├── 04_innovation.py
│       ├── 05_infrastructure.py
│       ├── 06_gap_analysis.py
│       └── 07_recommendations.py
│
├── notebooks/                 # Exploratory analysis
├── tests/                     # pytest unit tests
├── docs/
│   ├── methodology.md
│   └── data_dictionary.md
│
├── validate_scaffold.py       # CI-ready setup checker
├── requirements.txt
├── pyproject.toml             # Black + isort + flake8 config
└── README.md
```

---

## Installation

```bash
# 1. Clone
git clone https://github.com/yourusername/india-ai-readiness-dashboard.git
cd india-ai-readiness-dashboard

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Validate setup
python validate_scaffold.py

# 5. Run dashboard
streamlit run dashboard/app.py
```

---

## Deployment (Streamlit Cloud — Free)

1. Push repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Set **Main file path** to `dashboard/app.py`
5. Click Deploy

The dashboard auto-redeploys on every `git push`.

---

## Power BI Integration

The processed CSV at `data/processed/ai_readiness_index.csv` can be connected directly to Power BI:

1. Open Power BI Desktop
2. **Get Data → Text/CSV**
3. Select `data/processed/ai_readiness_index.csv`
4. Build visuals on top of the pre-computed scores, ranks, and cluster labels

The same pipeline that powers Streamlit feeds Power BI — single source of truth, no data inconsistency.

---

## Skills Demonstrated

| Category | Skills |
|----------|--------|
| **Data Engineering** | ETL pipeline design, multi-source data integration, missing value imputation |
| **Feature Engineering** | Min-Max normalization, entropy weighting, composite index construction |
| **Statistical Analysis** | Spearman/Pearson correlation, K-Means clustering, sensitivity analysis |
| **Python** | Type hints, logging, pathlib, modular design, LRU caching, exception handling |
| **Visualization** | Plotly, choropleth maps, radar charts, heatmaps, dark-theme design system |
| **Dashboard** | Streamlit multi-page app, `@st.cache_data`, cloud deployment |
| **BI Tools** | Power BI connected to processed CSV pipeline |
| **Software Quality** | Black, isort, flake8, pytest, CI-ready validation script |
| **Documentation** | Inline docstrings, methodology.md, data_dictionary.md, README |

---

## Future Improvements

- [ ] **5G availability** data layer (currently missing from TRAI open data)
- [ ] **Data center density** as infrastructure sub-feature (NASSCOM reports)
- [ ] **Historical trends** — TRAI data goes back to 2015, enabling time-series analysis
- [ ] **Forecast module** — ARIMA/Prophet to project AI readiness scores to 2027
- [ ] **District-level** index for states with sufficient data granularity
- [ ] **Automated refresh** — GitHub Actions workflow to update CSVs quarterly
- [ ] **pytest coverage** — unit tests for cleaner.py and index_builder.py edge cases
- [ ] **PDF extractor** — `pdfplumber` script for TRAI quarterly broadband reports
- [ ] **AHP weights** as third sensitivity check alongside entropy and equal weighting

---

## Methodology Reference

[OECD (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*. OECD Publishing.](https://www.oecd.org/sdd/42495745.pdf)

Shannon, C. E. (1948). A mathematical theory of communication. *Bell System Technical Journal*, 27(3), 379–423.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
Built with Python · Streamlit · Plotly · Pandas · scikit-learn
</p>
