"""
Phase 6: main regressions.

Specification (built up one column at a time so coefficient movement is visible):

    obesity_pct[s,t] = beta * glp1_per_1000_pop[s,t] + X[s,t]'gamma + alpha_s + delta_t + eps[s,t]

  (1) Pooled OLS: no fixed effects, no controls.
  (2) + state fixed effects (alpha_s) -- the "within" transformation.
  (3) + year fixed effects (delta_t) -- two-way fixed effects (TWFE).
  (4) + controls: log real income per capita, unemployment rate, % 65+.

All columns use standard errors clustered by state (linearmodels, cov_type=
"clustered", cluster_entity=True).

Primary treatment variable note: the project brief's preferred measure is
GLP-1 prescriptions per 1,000 Medicaid *enrollees*, but that denominator
(CMS T-MSIS-based) is only available 2016-2022 -- using it as the primary
measure would drop the 2023-2024 peak-uptake years and roughly halve the
sample, directly undermining the precision goal from Phase 4. So the main
specification here uses prescriptions per 1,000 *population* (full
2011-2024 coverage); per-1,000-enrollees is reported as a robustness check
on the 2016-2022 subsample in Phase 8. This is a deliberate, documented
deviation from the brief -- see README / report/findings.md.

A Hausman test (fixed effects vs. random effects) is reported for the
entity-effects-only specification with controls (the classic one-way FE/RE
comparison; the two-way TWFE model has no random-effects analogue to
compare against in the standard formulation taught at this level).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS, PooledOLS, RandomEffects
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

TREATMENT = "glp1_per_1000_pop"
CONTROLS = ["log_income_pc", "unemployment_rate", "pct_65plus"]


def load_indexed_panel() -> pd.DataFrame:
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    needed = ["obesity_pct", TREATMENT] + CONTROLS
    panel = panel.dropna(subset=needed).copy()
    return panel.set_index(["state", "year"])


def fit_column(df: pd.DataFrame, formula: str, entity_effects: bool, time_effects: bool):
    if not entity_effects and not time_effects:
        mod = PooledOLS.from_formula(formula, data=df)
    else:
        extra = []
        if entity_effects:
            extra.append("EntityEffects")
        if time_effects:
            extra.append("TimeEffects")
        mod = PanelOLS.from_formula(formula + " + " + " + ".join(extra), data=df)
    return mod.fit(cov_type="clustered", cluster_entity=True)


def hausman_test(df: pd.DataFrame) -> str:
    """Classic FE-vs-RE Hausman test, entity effects only, with controls."""
    formula = f"obesity_pct ~ 1 + {TREATMENT} + " + " + ".join(CONTROLS)
    fe = PanelOLS.from_formula(formula + " + EntityEffects", data=df).fit()
    re = RandomEffects.from_formula(formula, data=df).fit()

    common = [p for p in fe.params.index if p in re.params.index]
    b_fe, b_re = fe.params[common], re.params[common]
    v_fe, v_re = fe.cov.loc[common, common], re.cov.loc[common, common]

    diff = (b_fe - b_re).values
    var_diff = (v_fe - v_re).values
    try:
        stat = diff @ np.linalg.inv(var_diff) @ diff
        df_ = len(common)
        if stat < 0:
            return (f"Hausman test (FE vs RE), entity-effects specification with controls:\n"
                    f"  chi2({df_}) = {stat:.3f} (negative)\n"
                    f"  A negative Hausman statistic is a known finite-sample anomaly (it means the "
                    f"asymptotic Var(FE)-Var(RE)>=0 assumption doesn't hold exactly in this sample) -- "
                    f"conventionally treated as a failure to reject H0, i.e. no strong evidence against "
                    f"RE. FE is still used as the main specification here because the state-level "
                    f"confounding story (sicker states prescribe more) is the more defensible prior "
                    f"regardless of what this test shows.\n")
        pval = 1 - stats.chi2.cdf(stat, df_)
        verdict = (
            "Reject H0 (p<0.05): systematic difference between FE and RE -> FE is preferred "
            "(RE's assumption that the state effects are uncorrelated with the regressors looks wrong)."
            if pval < 0.05 else
            "Fail to reject H0 (p>=0.05): no strong evidence against RE, but FE remains the safer, "
            "more defensible default given the obvious state-level confounding story."
        )
        return (f"Hausman test (FE vs RE), entity-effects specification with controls:\n"
                f"  chi2({df_}) = {stat:.3f}, p = {pval:.4f}\n  {verdict}\n")
    except np.linalg.LinAlgError:
        return ("Hausman test could not be computed (singular covariance difference matrix) -- "
                "a known finite-sample issue with few clusters; reported for transparency, not "
                "leaned on for the paper's conclusion.\n")


def main() -> None:
    df = load_indexed_panel()
    print(f"[regressions] estimation sample: {len(df)} obs, "
          f"{df.index.get_level_values('state').nunique()} states, "
          f"{df.index.get_level_values('year').nunique()} years")

    results = {}
    results["(1) Pooled OLS"] = fit_column(df, f"obesity_pct ~ 1 + {TREATMENT}", False, False)
    results["(2) + State FE"] = fit_column(df, f"obesity_pct ~ 1 + {TREATMENT}", True, False)
    results["(3) + Year FE (TWFE)"] = fit_column(df, f"obesity_pct ~ 1 + {TREATMENT}", True, True)
    ctrl_formula = f"obesity_pct ~ 1 + {TREATMENT} + " + " + ".join(CONTROLS)
    results["(4) + Controls"] = fit_column(df, ctrl_formula, True, True)

    rows = []
    for name, res in results.items():
        row = {"column": name, "beta": res.params[TREATMENT], "se": res.std_errors[TREATMENT],
               "t": res.tstats[TREATMENT], "pvalue": res.pvalues[TREATMENT],
               "n": int(res.nobs), "r2_within": getattr(res, "rsquared_within", np.nan)}
        rows.append(row)
    table = pd.DataFrame(rows)

    out_csv = config.OUTPUTS_TABLES / "main_results.csv"
    table.to_csv(out_csv, index=False)
    print(f"\n[regressions] table -> {out_csv}")
    print(table.round(4))

    out_txt = config.OUTPUTS_TABLES / "main_results.txt"
    with open(out_txt, "w") as f:
        f.write("Main regression results: obesity_pct on GLP-1 prescriptions per 1,000 population\n")
        f.write("=" * 80 + "\n\n")
        f.write(table.round(4).to_string(index=False))
        f.write("\n\nCoefficient movement (1)->(4): ")
        f.write(f"{rows[0]['beta']:.4f} -> {rows[-1]['beta']:.4f}. ")
        if abs(rows[-1]["beta"]) < abs(rows[0]["beta"]):
            f.write("The coefficient shrinks once state fixed effects are added, consistent with "
                    "confounding: states that prescribe more GLP-1s (often sicker/higher-diabetes "
                    "populations) also tend to have different obesity levels for reasons unrelated "
                    "to the drugs themselves. Once we compare each state to itself over time (the "
                    "within-transformation), rather than comparing different states to each other, "
                    "much of that confounding is removed.\n")
        else:
            f.write("The coefficient does not shrink monotonically once fixed effects are added; "
                    "see report/findings.md for a full discussion.\n")
        f.write("\n\n" + hausman_test(df))

    print(f"[regressions] readable table + narrative -> {out_txt}")
    print("\n" + hausman_test(df))


if __name__ == "__main__":
    main()
