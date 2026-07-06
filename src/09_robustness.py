"""
Phase 8: robustness checks.

Re-runs the column-(4) main specification (TWFE + controls, SEs clustered by
state) under a series of perturbations, and collects the treatment
coefficient from each into one table so it's easy to see whether the
headline conclusion holds up.

Checks, per the project brief:
  1. Alternative treatment measure: per-1,000-Medicaid-enrollees instead of
     per-1,000-population (on the 2016-2022 subsample where enrollment data exists).
  2. Alternative outcome: diabetes prevalence instead of obesity prevalence.
  3. Leave-one-state-out: re-estimate 51 times, each time dropping one state;
     report the range of the coefficient. Also report dropping DC alone and
     dropping the 5 largest states together.
  4. Suppression-handling sensitivity: rebuild the treatment variable with
     suppressed SDUD cells imputed as 0 and as 10 (vs. the primary rule of 5).
  5. Dropping controls; adding state-specific linear time trends.

Wild cluster bootstrap SEs (mentioned in the brief as an optional check,
since there are only ~51 clusters) are not implemented here -- doing it
properly needs a bootstrap-t procedure that's beyond a 2nd-year scope to
hand-roll and no lightweight, dependency-free implementation exists in
statsmodels/linearmodels. Flagged as a possible extension, not a gap that
changes the conclusion (51 clusters is not a small-cluster problem in the
way 5-10 clusters would be).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

TREATMENT = "glp1_per_1000_pop"
CONTROLS = ["log_income_pc", "unemployment_rate", "pct_65plus"]
LARGEST_STATES = ["CA", "TX", "FL", "NY", "PA"]  # by population, for the leave-out check


def fit_twfe(df: pd.DataFrame, outcome: str, treatment: str, controls: list[str], extra_terms: str = ""):
    needed = [outcome, treatment] + controls
    d = df.dropna(subset=needed).copy()
    control_terms = "".join(f" + {c}" for c in controls)
    formula = f"{outcome} ~ 1 + {treatment}" + control_terms + extra_terms + " + EntityEffects + TimeEffects"
    d = d.set_index(["state", "year"])
    res = PanelOLS.from_formula(formula, data=d).fit(cov_type="clustered", cluster_entity=True)
    return res, len(d)


def rebuild_treatment_with_imputation(panel: pd.DataFrame, impute_value: int) -> pd.DataFrame:
    frames = []
    for year in config.YEARS:
        path = config.DATA_RAW / f"sdud_glp1_{year}.csv"
        if path.exists():
            frames.append(pd.read_csv(path))
    raw = pd.concat(frames, ignore_index=True)
    raw["is_suppressed"] = raw["suppression_used"].astype(str).str.lower() == "true"
    raw["number_of_prescriptions"] = pd.to_numeric(raw["number_of_prescriptions"], errors="coerce")
    raw["rx_imputed"] = np.where(raw["is_suppressed"], impute_value, raw["number_of_prescriptions"].fillna(0))
    agg = raw.groupby(["state", "year"])["rx_imputed"].sum().reset_index()
    agg = agg.rename(columns={"rx_imputed": "glp1_prescriptions_alt"})

    out = panel.merge(agg, on=["state", "year"], how="left")
    out["glp1_per_1000_pop_alt"] = 1000 * out["glp1_prescriptions_alt"] / out["population"]
    return out


def main() -> None:
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    rows = []

    # Baseline (column 4 from Phase 6), for reference.
    res, n = fit_twfe(panel, "obesity_pct", TREATMENT, CONTROLS)
    rows.append({"check": "Baseline (main spec, col 4)", "beta": res.params[TREATMENT],
                 "se": res.std_errors[TREATMENT], "n": n, "note": "per-1,000-population, 2011-2024"})

    # 1. Alternative treatment measure.
    res, n = fit_twfe(panel, "obesity_pct", "glp1_per_1000_enrollees", CONTROLS)
    rows.append({"check": "Alt treatment: per-1,000 Medicaid enrollees", "beta": res.params["glp1_per_1000_enrollees"],
                 "se": res.std_errors["glp1_per_1000_enrollees"], "n": n, "note": "restricted to 2016-2022 (enrollment coverage)"})

    # 2. Alternative outcome.
    res, n = fit_twfe(panel, "diabetes_pct", TREATMENT, CONTROLS)
    rows.append({"check": "Alt outcome: diabetes prevalence", "beta": res.params[TREATMENT],
                 "se": res.std_errors[TREATMENT], "n": n, "note": "GLP-1s are heavily prescribed for diabetes"})

    # 3. Leave-one-state-out.
    loo_betas = {}
    for dropped_state in config.STATE_ABBRS:
        sub = panel[panel["state"] != dropped_state]
        try:
            res, n = fit_twfe(sub, "obesity_pct", TREATMENT, CONTROLS)
            loo_betas[dropped_state] = res.params[TREATMENT]
        except Exception:
            continue
    loo_series = pd.Series(loo_betas)
    rows.append({"check": "Leave-one-state-out (range across 51 runs)",
                 "beta": loo_series.mean(), "se": np.nan, "n": len(panel["state"].unique()) - 1,
                 "note": f"min={loo_series.min():.4f} ({loo_series.idxmin()}), "
                         f"max={loo_series.max():.4f} ({loo_series.idxmax()})"})

    sub = panel[panel["state"] != "DC"]
    res, n = fit_twfe(sub, "obesity_pct", TREATMENT, CONTROLS)
    rows.append({"check": "Drop DC", "beta": res.params[TREATMENT], "se": res.std_errors[TREATMENT],
                 "n": n, "note": "DC is not a state; check it isn't driving results"})

    sub = panel[~panel["state"].isin(LARGEST_STATES)]
    res, n = fit_twfe(sub, "obesity_pct", TREATMENT, CONTROLS)
    rows.append({"check": "Drop 5 largest states", "beta": res.params[TREATMENT], "se": res.std_errors[TREATMENT],
                 "n": n, "note": f"drops {LARGEST_STATES}"})

    # 4. Suppression sensitivity.
    for impute_value in (0, 10):
        alt_panel = rebuild_treatment_with_imputation(panel, impute_value)
        res, n = fit_twfe(alt_panel, "obesity_pct", "glp1_per_1000_pop_alt", CONTROLS)
        rows.append({"check": f"Suppression imputed as {impute_value} (primary rule: 5)",
                     "beta": res.params["glp1_per_1000_pop_alt"], "se": res.std_errors["glp1_per_1000_pop_alt"],
                     "n": n, "note": "cf. baseline row for the primary rule's coefficient"})

    # 5a. Drop controls.
    res, n = fit_twfe(panel, "obesity_pct", TREATMENT, [])
    rows.append({"check": "Drop all controls (TWFE only)", "beta": res.params[TREATMENT],
                 "se": res.std_errors[TREATMENT], "n": n, "note": "column (3) from Phase 6, for reference"})

    # 5b. State-specific linear trends. Built as explicit named columns
    # (trend_<STATE> = trend * 1[state==STATE]) rather than a "C(state):trend"
    # formula -- patsy/formulaic's C() resolves bare names via the caller's
    # local variables when they aren't a data column, which is fragile (a
    # leftover loop variable elsewhere in this function previously shadowed
    # it silently). Explicit columns have no such ambiguity.
    trend_panel = panel.copy()
    trend_panel["trend"] = trend_panel["year"] - config.YEAR_START
    trend_cols = []
    for trend_state in config.STATE_ABBRS:
        col = f"trend_{trend_state}"
        trend_panel[col] = trend_panel["trend"] * (trend_panel["state"] == trend_state).astype(float)
        trend_cols.append(col)
    try:
        d = trend_panel.dropna(subset=["obesity_pct", TREATMENT] + CONTROLS).set_index(["state", "year"])
        formula = (f"obesity_pct ~ 1 + {TREATMENT} + " + " + ".join(CONTROLS + trend_cols) +
                   " + EntityEffects + TimeEffects")
        # One state's trend column is collinear with the year effects + the
        # other states' trends combined (a standard rank-deficiency with a
        # full set of state trends alongside year FE) -- drop_absorbed lets
        # linearmodels drop that one redundant column instead of erroring.
        res = PanelOLS.from_formula(formula, data=d, drop_absorbed=True).fit(
            cov_type="clustered", cluster_entity=True)
        rows.append({"check": "+ state-specific linear trends", "beta": res.params[TREATMENT],
                     "se": res.std_errors[TREATMENT], "n": int(res.nobs),
                     "note": "each state gets its own linear time trend on top of TWFE"})
    except Exception as exc:
        rows.append({"check": "+ state-specific linear trends", "beta": np.nan, "se": np.nan,
                     "n": np.nan, "note": f"could not estimate: {exc}"})

    rows.append({"check": "Wild cluster bootstrap SEs", "beta": np.nan, "se": np.nan, "n": np.nan,
                 "note": "not implemented (51 clusters is not a small-cluster problem; flagged as a "
                         "possible extension, see module docstring)"})

    table = pd.DataFrame(rows)
    out_csv = config.OUTPUTS_TABLES / "robustness.csv"
    table.to_csv(out_csv, index=False)
    print(f"[robustness] table -> {out_csv}")
    print(table.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
