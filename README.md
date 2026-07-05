# GLP-1RA Uptake and State-Level Obesity: An Econometric Analysis

**Status: scaffolding (Phase 1 of 10) — data, results, and findings below will be filled in as later phases complete.**

## Research question

Did the rapid uptake of GLP-1 receptor agonists (semaglutide, tirzepatide, etc.) reduce
adult obesity prevalence across US states, and can we detect this effect given the
short time the drugs have been widely used?

This is a 2nd-year undergraduate econometrics project. The goal is a clean, defensible
design with tight confidence intervals — a precisely-estimated null result is a valid
and honest finding here, not a failure.

## Data sources

| Variable | Source | Coverage |
|---|---|---|
| Obesity prevalence (primary outcome) | CDC BRFSS, `chronicdata.cdc.gov` | 2011-2024, 51 states |
| Diabetes prevalence (secondary outcome) | CDC US Diabetes Surveillance System | 2011-2024, 51 states |
| GLP-1RA prescriptions (treatment) | Medicaid State Drug Utilization Data (SDUD) | 2011-2024, 51 states |
| Medicaid enrollment (treatment denominator) | CMS `ProgramType-anul.csv` | 2016-2022 only (gap documented) |
| State population | Census Population Estimates Program | 2011-2024, 51 states |
| Age structure (65+ share, median age) | Census PEP age/sex files | 2011-2024, 51 states |
| Unemployment rate | BLS LAUS (substitute for FRED — see note) | 2011-2024, 51 states |
| Median household income | Census SAIPE (substitute for FRED — see note) | 2011-2024, 51 states |

**FRED substitution note:** the original plan called for FRED (real personal income
per capita, unemployment rate). FRED requires a free API key that needs a human to
register for; none was available when this was built, so BLS (unemployment) and
Census SAIPE (income) are used instead — both keyless. See `config.py` for details
and how to switch back to FRED if a key becomes available.

**SDUD Medicaid-only caveat:** SDUD covers only Medicaid-reimbursed prescriptions.
Federal Medicaid excludes weight-loss drugs by default (states may opt in), so this
proxy captures GLP-1s prescribed largely for diabetes rather than weight loss, and
only for the Medicaid population. This is a real measurement limitation, discussed
in `report/findings.md`.

## Methods

OLS → entity fixed effects → two-way fixed effects (TWFE), cluster-robust SEs by
state, an event-study/parallel-trends check, and robustness/placebo tests. No
staggered-DiD estimators are used: GLP-1RA uptake surged nationally at roughly the
same time (2021-2023), so there is no staggered treatment timing problem — year
fixed effects absorb the common shock, and identification comes from differential
uptake intensity across states. See `report/findings.md` for the full argument.

## Reproducing

```
pip install -r requirements.txt
python src/01_pull_obesity.py
python src/02_pull_glp1.py
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

_To be filled in after Phase 4 (feasibility check) and Phase 6-9 (regressions,
event study, robustness)._

## Limitations

_To be filled in — see `report/findings.md` for the full discussion once complete._
