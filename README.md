# GLP-1RA Uptake and State-Level Obesity: An Econometric Analysis

**Status: complete (all 10 phases).** Full write-up in `report/findings.md`.

## Research question

Did the rapid uptake of GLP-1 receptor agonists (semaglutide, tirzepatide, etc.) reduce
adult obesity prevalence across US states, and can we detect this effect given the
short time the drugs have been widely used?

This is a 2nd-year undergraduate econometrics project. The goal is a clean, defensible
design with tight confidence intervals — a precisely-estimated null result is a valid
and honest finding here, not a failure. See below: that is exactly what this project finds.

## Data sources

| Variable | Source | Coverage |
|---|---|---|
| Obesity prevalence (primary outcome) | CDC BRFSS, `chronicdata.cdc.gov` | 2011-2024, 51 states (5 state-years missing) |
| Diabetes prevalence (secondary outcome) | CDC US Diabetes Surveillance System | 2011-2024, 51 states |
| GLP-1RA prescriptions (treatment) | Medicaid State Drug Utilization Data (SDUD) | 2011-2024, 51 states |
| Medicaid enrollment (treatment denominator) | CMS `ProgramType-anul.csv` | 2016-2022 only (gap documented) |
| State population | Census Population Estimates Program | 2011-2024, 51 states |
| Age structure (65+ share) | Census PEP age/sex files | 2011-2024, 51 states |
| Real personal income per capita, unemployment rate | FRED (`{state}PCPI`, `{state}UR`) | 2011-2024, 51 states |

**SDUD Medicaid-only caveat:** SDUD covers only Medicaid-reimbursed prescriptions.
Federal Medicaid excludes weight-loss drugs by default (states may opt in), so this
proxy captures GLP-1s prescribed largely for diabetes rather than weight loss, and
only for the Medicaid population. This is a real measurement limitation, discussed
in `report/findings.md`.

**Primary treatment measure note:** the project brief's preferred measure is GLP-1
prescriptions per 1,000 Medicaid *enrollees*, but that denominator is only available
2016-2022. Using it as primary would drop 2023-2024 — the peak-uptake years — and
roughly halve the sample. The main specification instead uses prescriptions per 1,000
*population* (full 2011-2024 coverage); per-1,000-enrollees is a robustness check on
the 2016-2022 subsample. See `report/findings.md` §2 for the full reasoning.

## Methods

OLS → entity fixed effects → two-way fixed effects (TWFE), cluster-robust SEs by
state, an event-study/parallel-trends check, and robustness/placebo tests, plus an
optional, clearly-labeled shift-share IV stretch. No staggered-DiD estimators are
used: GLP-1RA uptake surged nationally at roughly the same time (2021-2023), so
there is no staggered treatment timing problem — year fixed effects absorb the
common shock, and identification comes from differential uptake intensity across
states. See `report/findings.md` for the full argument.

## Reproducing

```
pip install -r requirements.txt
cp .env.example .env   # then fill in your own FRED_API_KEY (free at fred.stlouisfed.org)
python src/01_pull_obesity.py
python src/02_pull_glp1.py       # slow: ~19 product queries x 14 years against the Medicaid API
python src/03_pull_controls.py
python src/04_build_panel.py
python src/05_descriptives.py
python src/06_feasibility_power.py
python src/07_main_regressions.py
python src/08_event_study.py
python src/09_robustness.py
python src/10_iv_stretch.py   # optional
```

Raw API pulls are cached in `data/raw/`; delete a file there to force a re-pull.

## Repository structure

```
glp1-obesity/
├── config.py                # year range, states, product list, endpoints
├── data/raw/                 # cached raw pulls
├── data/processed/           # panel.csv
├── src/01...10_*.py          # pipeline, run in order
├── outputs/figures/
├── outputs/tables/
└── report/findings.md        # write-up
```

## Key findings

Across every specification, GLP-1RA uptake shows **no detectable association with
state-level adult obesity prevalence** once the shared national trend is removed:

| Column | beta | SE | p |
|---|---|---|---|
| (1) Pooled OLS | 0.144 | 0.026 | <0.001 |
| (2) + State FE | 0.177 | 0.017 | <0.001 |
| (3) + Year FE (TWFE) | -0.004 | 0.012 | 0.74 |
| (4) + Controls | -0.008 | 0.013 | 0.56 |

The positive, significant coefficient in columns (1)-(2) is a textbook confound:
obesity and GLP-1 uptake both trended up nationally over 2011-2024. Year fixed
effects remove that shared trend; what's left — relative uptake intensity across
states within a year — shows no relationship with relative obesity levels. The
event study confirms this: pre- and post-2021 coefficients are statistically
indistinguishable, both hovering near zero.

This is a **precisely estimated null**, not an underpowered one: the feasibility
check (Phase 4) shows the design could detect an effect roughly 10x smaller than
would be needed to matter. Every robustness check (alternative treatment/outcome
measures, leave-one-state-out, suppression-handling sensitivity, state-specific
trends) lands within about ±0.02 of zero. Full detail, numbers, and figures in
`report/findings.md`.

## Limitations

1. **Medicaid-only treatment proxy** — SDUD skews toward diabetes indications and the Medicaid population, not general weight-loss use.
2. **Short post-treatment window** — weight-loss uptake scaled mostly 2021-2024; obesity prevalence is slow-moving.
3. **Survey measurement error** — BRFSS confidence intervals average ±1.6pp per state-year.
4. **Endogeneity of uptake** — TWFE removes time-invariant and common-year confounds, not time-varying state-specific ones; the optional IV stretch is inconclusive (weak instrument).
5. **Ecological/aggregation inference** — state-level aggregates say nothing about individual-level effects (already well-established in clinical trials).
6. **Medicaid enrollment coverage gap** — forces the primary-measure switch noted above.

Full discussion in `report/findings.md` §8.
