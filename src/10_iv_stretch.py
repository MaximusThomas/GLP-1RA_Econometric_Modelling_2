"""
Phase 9 (optional stretch): instrumental variables.

GLP-1RA uptake is not randomly assigned across states -- states differ in
prescribing culture, provider supply, disease burden, and Medicaid policy in
ways that plausibly also relate to obesity trends. TWFE with controls
absorbs a lot of this (anything time-invariant per state, anything common
per year), but time-varying confounding within a state is still possible.

This script implements one simple shift-share ("Bartik") instrument as a
labeled *stretch goal*, not part of the core conclusion:

    Z[s,t] = diabetes_pct[s, 2011] * national_glp1_trend[t, excl. s]

The "share" is each state's 2011 (pre-GLP-1-boom) diabetes prevalence -- a
proxy for latent demand for these drugs. The "shift" is the leave-one-out
national average uptake trend in year t. The idea: a state with more
diabetes in 2011 should absorb more of the *national* uptake wave, for
reasons plausibly unrelated to that state's obesity trend specifically.

This exclusion restriction is arguable, not proven -- a state's 2011
diabetes rate could easily be correlated with its future obesity trend
through channels other than GLP-1 uptake (diet, activity, healthcare access
trends). Treat the result here as illustrative of the IV *logic*, not as a
stronger causal claim than the TWFE result in Phase 6.

Implementation note: linearmodels' PanelOLS does not support endogenous
regressors, so fixed effects are partialled out by two-way demeaning
(subtract the state mean and year mean, add back the grand mean -- the
standard Frisch-Waugh-Lovell trick for two-way FE), and IV2SLS is run on
the demeaned data. Clustering after manual demeaning is an approximation
(it does not adjust degrees of freedom for the absorbed fixed effects), a
further reason this section is a stretch/appendix, not the headline result.
"""

import sys
from pathlib import Path

import pandas as pd
from linearmodels.iv import IV2SLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

TREATMENT = "glp1_per_1000_pop"
CONTROLS = ["log_income_pc", "unemployment_rate", "pct_65plus"]


def two_way_demean(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        state_mean = out.groupby("state")[col].transform("mean")
        year_mean = out.groupby("year")[col].transform("mean")
        grand_mean = out[col].mean()
        out[col + "_dm"] = out[col] - state_mean - year_mean + grand_mean
    return out


def build_instrument(panel: pd.DataFrame) -> pd.DataFrame:
    baseline = panel.loc[panel["year"] == config.YEAR_START, ["state", "diabetes_pct"]]
    baseline = baseline.rename(columns={"diabetes_pct": "baseline_diabetes"})
    df = panel.merge(baseline, on="state", how="left")

    year_totals = df.groupby("year")[TREATMENT].agg(["sum", "count"])
    df = df.merge(year_totals, on="year", how="left")
    # Leave-one-out national mean: (year total - own value) / (n - 1).
    df["national_trend_loo"] = (df["sum"] - df[TREATMENT]) / (df["count"] - 1)
    df["instrument"] = df["baseline_diabetes"] * df["national_trend_loo"]
    return df.drop(columns=["sum", "count"])


def main() -> None:
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    df = build_instrument(panel)

    needed = ["obesity_pct", TREATMENT, "instrument"] + CONTROLS
    df = df.dropna(subset=needed).copy()

    dm = two_way_demean(df, ["obesity_pct", TREATMENT, "instrument"] + CONTROLS)

    dep = dm["obesity_pct_dm"]
    endog = dm[[TREATMENT + "_dm"]]
    exog = dm[[c + "_dm" for c in CONTROLS]]
    exog.insert(0, "const", 1.0)
    instr = dm[["instrument_dm"]]

    mod = IV2SLS(dependent=dep, exog=exog, endog=endog, instruments=instr)
    res = mod.fit(cov_type="clustered", clusters=dm["state"])

    print(res)

    first_stage = mod.first_stage
    print("\nFirst-stage diagnostics (instrument relevance):")
    print(first_stage)

    out_txt = config.OUTPUTS_TABLES / "iv_stretch.txt"
    with open(out_txt, "w") as f:
        f.write("OPTIONAL STRETCH: shift-share IV for GLP-1 uptake (see module docstring for caveats)\n")
        f.write("=" * 90 + "\n\n")
        f.write(str(res))
        f.write("\n\nFirst stage:\n")
        f.write(str(first_stage))
        f.write(f"\n\nIV coefficient on {TREATMENT}: {res.params[TREATMENT + '_dm']:.4f} "
                f"(SE {res.std_errors[TREATMENT + '_dm']:.4f})\n")
        f.write("Compare to the TWFE+controls (OLS) estimate in outputs/tables/main_results.csv, "
                "column (4). This IV result is illustrative only -- the exclusion restriction "
                "(2011 diabetes prevalence affects obesity only through GLP-1 uptake) is arguable, "
                "not verified, and this section should not be read as strengthening the causal "
                "claim beyond what Phase 6-8 support.\n")
    print(f"\n[iv stretch] -> {out_txt}")


if __name__ == "__main__":
    main()
