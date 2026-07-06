## Phase 4: Feasibility and power check

### 1. Treatment variation

**GLP-1 prescriptions per 1,000 population**

       mean    std   min    max  count
year                                  
2011   0.48   0.35  0.03   1.95     51
2012   0.56   0.39  0.03   1.89     51
2013   0.60   0.42  0.06   2.08     51
2014   0.82   0.55  0.11   2.45     51
2015   1.22   0.78  0.16   3.61     51
2016   1.91   1.22  0.20   5.19     51
2017   2.60   1.60  0.29   7.09     51
2018   3.44   2.15  0.59   8.65     51
2019   4.63   2.75  1.01  12.29     51
2020   6.15   3.59  0.00  16.55     51
2021   9.02   4.85  1.89  20.32     51
2022  13.49   7.31  2.59  33.55     51
2023  20.46  12.41  3.54  65.75     51
2024  23.65  14.66  4.37  58.76     51

- 2023-2024 cross-state spread: mean=22.06, SD=13.61, CV=0.62, min=3.54, max=65.75 (n=102)

**GLP-1 prescriptions per 1,000 Medicaid enrollees**

       mean    std   min    max  count
year                                  
2011    NaN    NaN   NaN    NaN      0
2012    NaN    NaN   NaN    NaN      0
2013    NaN    NaN   NaN    NaN      0
2014    NaN    NaN   NaN    NaN      0
2015    NaN    NaN   NaN    NaN      0
2016   8.61   4.82  0.65  21.43     51
2017  11.50   5.93  0.93  29.00     51
2018  15.37   7.48  1.99  37.18     51
2019  21.19   9.74  4.03  48.43     51
2020  26.63  12.13  0.00  56.75     51
2021  35.03  14.64  6.47  67.95     51
2022  49.05  20.54  9.65  91.71     51
2023    NaN    NaN   NaN    NaN      0
2024    NaN    NaN   NaN    NaN      0

### 2. Outcome movement vs. survey noise

Within-state change in obesity prevalence, 2019 -> 2024: mean=1.97 pp, SD=1.26 pp, min=-0.80, max=4.50 (n=49 states).

Typical BRFSS 95% CI full width for obesity_pct: mean=3.13 pp, median=3.00 pp (i.e. roughly +/-1.56 pp of sampling noise around each single state-year estimate).

Average |2019->2024 change| is about 1.32x the average survey-noise half-width. This suggests real changes are visible above the noise floor.

### 3. Back-of-envelope minimum detectable effect (MDE)

N = 709, states = 51, years = 14

Single-covariate TWFE (state + year FE, clustered SE by state): SE(beta) = 0.0123

Back-of-envelope MDE (80% power, 5% two-sided test) ~= 2.8 x SE = **0.034** percentage points of obesity prevalence per 1-unit increase in GLP-1 prescriptions per 1,000 population.

For context, a one-SD increase in the treatment variable is 9.27 units, so the MDE for a one-SD change in uptake is about 0.318 pp.

### 4. Timing note

GLP-1RA prescribing for diabetes existed throughout the panel (exenatide since
2005, liraglutide since 2010), but weight-loss-labeled use and the associated
demand surge is concentrated in 2021-2024 (Wegovy approved June 2021, Mounjaro
2022, Zepbound late 2023). The obesity outcome is a slow-moving population
average that responds, if at all, with a lag (behavioural + biological +
survey-timing lags). A 3-4 year post-surge window is short relative to how
slowly population-level obesity prevalence moves. A small or statistically
null estimated effect in this window is a plausible and honest finding, not
evidence the design failed -- see the MDE above for whether we could have
detected a larger effect if one existed.
