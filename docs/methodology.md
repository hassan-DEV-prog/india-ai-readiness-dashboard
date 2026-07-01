# India AI Readiness Index — Methodology

## 1. Objective

The India AI Readiness Index measures the structural preparedness of Indian states and Union Territories for an AI-driven economy. It is a composite index aggregating 14 indicators across 5 pillars into a single comparable score per state.

## 2. Pillar Structure and Feature Selection

Each pillar answers a distinct structural question:

| Pillar | Question | Features |
|--------|----------|----------|
| Internet Readiness | Can citizens and businesses access AI services digitally? | internet_penetration_pct, broadband_subscribers_per_100, rural_internet_pct |
| Education & Talent | Is there human capital to build and deploy AI? | literacy_rate_pct, aicte_institutes_per_million, engineering_seats_per_million |
| Infrastructure | Is the physical backbone in place? | electrification_pct, per_capita_power_consumption_kwh |
| Innovation Ecosystem | Is entrepreneurial activity converting talent into ventures? | startups_per_million, digital_literacy_beneficiaries_per_million |
| Economic Strength | Does the economic base support AI adoption? | gsdp_per_capita_inr, urbanization_pct |

## 3. Normalization

All features are normalized to [0, 1] using Min-Max scaling:

```
x_norm = (x - x_min) / (x_max - x_min)
```

**Outlier clipping** is applied before normalization: values beyond ±3 standard deviations from the mean are clipped to the boundary. This prevents a single extreme outlier (e.g., Delhi's GSDP) from compressing all other states toward zero.

**Zero-variance handling**: If all states have identical values on a feature, all states are assigned 0.5 (midpoint) to avoid division by zero and to correctly reflect the feature's zero discriminatory power.

## 4. Entropy Weighting

### 4.1 Rationale

Arbitrary expert weights lack statistical justification. Entropy weighting is a data-driven alternative from information theory: pillars that discriminate more between states receive higher weight.

**Reference:** OECD (2008), *Handbook on Constructing Composite Indicators*, Chapter 6.

### 4.2 Formula

For pillar j across m states (m = 36):

**Step 1 — Relative share:**
```
p_ij = P_ij / Σ_i P_ij
```

**Step 2 — Shannon entropy (normalized):**
```
E_j = -(1/ln(m)) × Σ_i (p_ij × ln(p_ij))
```
E_j ∈ [0, 1]. E_j → 1 when all states score identically (no information).

**Step 3 — Divergence:**
```
d_j = 1 - E_j
```
Higher divergence = greater discrimination power.

**Step 4 — Weight:**
```
w_j = d_j / Σ_j d_j
```
Weights sum to 1.0.

### 4.3 Resulting Weights (2023 data)

| Pillar | Entropy Weight | Interpretation |
|--------|---------------|----------------|
| Economic Strength | 28.5% | GSDP per capita spans a 10x range across states |
| Internet Readiness | 25.3% | High variance in penetration rates |
| Innovation Ecosystem | 19.7% | Startup density is highly concentrated |
| Infrastructure | 13.5% | Near-universal electrification reduces discrimination |
| Education & Talent | 13.0% | Literacy rates are relatively uniform |

Infrastructure receiving the lowest weight is **analytically correct**: when 97%+ of states have achieved ≥99% electrification, this metric carries near-zero information for ranking purposes.

## 5. Composite Score

```
AI_Score_i = Σ_j (w_j × P_ij) × 100
```

Scaled to [0, 100] for readability. P_ij is the pillar score for state i on pillar j (mean of normalized constituent features).

## 6. Sensitivity Analysis

A sensitivity check uses equal weights (w_j = 0.20 for all j) to test whether rankings are stable across weighting methods.

**Result:** Spearman rank correlation = **0.996** between entropy-weighted and equal-weighted rankings. Maximum rank shift: 3 positions. Mean rank shift: 0.61 positions.

**Conclusion:** The index is robust. The ranking story is the same regardless of which defensible weighting method is chosen.

## 7. Missing Value Strategy

**Strategy:** Regional median imputation with national median fallback.

**Rationale:** National median imputation ignores the strong geographic clustering of Indian state development. Bihar and Karnataka have fundamentally different development baselines. Imputing Bihar's internet penetration with the national median (which includes Karnataka and Kerala) would systematically overstate Bihar's position.

**Implementation:**
1. Assign each state to one of 7 regions (North, South, East, West, Central, Northeast, Islands)
2. Compute regional median for each numeric column
3. Impute missing values with regional median
4. If region has fewer than 2 non-null values, fall back to national median
5. Flag every imputed value with a boolean column: `{feature}_imputed = True`

**Threshold:** Features missing in more than 30% of states are dropped entirely rather than imputed.

## 8. Clustering

K-Means clustering (k=4) is applied to the 5 pillar score dimensions. The choice of k=4 is validated using silhouette analysis across k=2..7.

Cluster labels are assigned by ranking clusters on their mean AI Readiness Score:
- **AI Leaders** (top quartile)
- **Fast Challengers**
- **Emerging Markets**
- **Lagging Regions**

## 9. Proxy Variable Disclosure

| Variable | True Measure | Proxy Used | Limitation |
|----------|-------------|------------|------------|
| Digital literacy | % of population digitally literate | PMGDISHA beneficiaries/million | Measures program reach, not actual literacy attainment |
| Startup ecosystem | All startups | DPIIT-recognized startups only | Excludes unregistered startups |
| Internet penetration | Active internet users | TRAI subscriber count | May double-count multi-SIM users |

## 10. Limitations

1. **Data vintage heterogeneity:** Some features use 2011 Census data (literacy) while others use 2023 data (startups). Year-mixing introduces inconsistency.
2. **State-level aggregation:** District-level variation within large states (UP, MP, Rajasthan) is hidden by state averaging.
3. **Proxy variables:** Digital literacy and startup counts are imperfect proxies for the constructs they represent.
4. **No 5G data:** 5G availability is not yet covered by publicly available state-disaggregated datasets.
5. **Causal inference:** Index rankings are correlational, not causal. A high AI readiness score does not imply that AI adoption will succeed.
