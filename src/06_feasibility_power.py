"""
Phase 4: feasibility and power check -- run BEFORE the main regressions.

The whole point of this script is to answer, honestly and with real numbers,
whether this design can say anything about a plausible effect size given the
short post-treatment window. A null result from Phase 6 is only informative
if this check shows the design had enough precision to detect a plausible
effect in the first place.

Four things, per the project brief:
  1. Treatment variation -- how much cross-state spread is there in uptake,
     especially by 2023-2024 (identification lives in this spread).
  2. Outcome movement -- how big are within-state obesity changes relative
     to BRFSS survey noise (the confidence interval width)?
  3. A back-of-envelope minimum detectable effect (MDE), using an actual
     single-covariate TWFE regression (state + year FE, clustered SEs) so
     the number is real, not guessed. This is not the main specification
     (that's Phase 6, built up column by column) -- it exists only to size
     up precision before committing to the full analysis.
  4. A timing note: GLP-1RA weight-loss use scaled up mostly 2021-2024, so
     the post-period is short and obesity is slow-moving.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def treatment_variation(panel: pd.DataFrame) -> str:
    lines = ["### 1. Treatment variation\n"]
    for col, label in [
        ("glp1_per_1000_pop", "GLP-1 prescriptions per 1,000 population"),
        ("glp1_per_1000_enrollees", "GLP-1 prescriptions per 1,000 Medicaid enrollees"),
    ]:
        lines.append(f"**{label}**\n")
        by_year = panel.groupby("year")[col].agg(["mean", "std", "min", "max", "count"])
        lines.append(by_year.round(2).to_string())
        lines.append("")
        recent = panel[panel["year"].isin([2023, 2024])][col].dropna()
        if len(recent):
            cv = recent.std() / recent.mean() if recent.mean() else float("nan")
            lines.append(
                f"- 2023-2024 cross-state spread: mean={recent.mean():.2f}, "
                f"SD={recent.std():.2f}, CV={cv:.2f}, "
                f"min={recent.min():.2f}, max={recent.max():.2f} (n={len(recent)})\n"
            )
    return "\n".join(lines)


def outcome_movement(panel: pd.DataFrame) -> str:
    lines = ["### 2. Outcome movement vs. survey noise\n"]
    wide = panel.pivot(index="state", columns="year", values="obesity_pct")
    if 2019 in wide.columns and 2024 in wide.columns:
        delta = (wide[2024] - wide[2019]).dropna()
        lines.append(
            f"Within-state change in obesity prevalence, 2019 -> 2024: "
            f"mean={delta.mean():.2f} pp, SD={delta.std():.2f} pp, "
            f"min={delta.min():.2f}, max={delta.max():.2f} (n={len(delta)} states).\n"
        )
    ci_width = (panel["obesity_ci_high"] - panel["obesity_ci_low"]).dropna()
    lines.append(
        f"Typical BRFSS 95% CI full width for obesity_pct: mean={ci_width.mean():.2f} pp, "
        f"median={ci_width.median():.2f} pp (i.e. roughly +/-{ci_width.mean()/2:.2f} pp of sampling noise "
        f"around each single state-year estimate).\n"
    )
    if 2019 in wide.columns and 2024 in wide.columns:
        ratio = delta.abs().mean() / (ci_width.mean() / 2)
        lines.append(
            f"Average |2019->2024 change| is about {ratio:.2f}x the average survey-noise half-width. "
            + ("This suggests real changes are visible above the noise floor.\n" if ratio > 1
               else "This suggests year-to-year changes are comparable to or smaller than survey noise "
                    "for many states -- a warning sign for precision.\n")
        )
    return "\n".join(lines)


def mde_check(panel: pd.DataFrame) -> str:
    lines = ["### 3. Back-of-envelope minimum detectable effect (MDE)\n"]
    df = panel.dropna(subset=["obesity_pct", "glp1_per_1000_pop"]).copy()
    df = df.set_index(["state", "year"])
    try:
        mod = PanelOLS.from_formula(
            "obesity_pct ~ 1 + glp1_per_1000_pop + EntityEffects + TimeEffects", data=df
        )
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        se = res.std_errors["glp1_per_1000_pop"]
        # Rough two-sided 5%-significance, 80%-power MDE multiplier (z_0.975 + z_0.80 ~ 2.8).
        mde = 2.8 * se
        lines.append(f"N = {res.nobs}, states = {df.index.get_level_values('state').nunique()}, "
                      f"years = {df.index.get_level_values('year').nunique()}\n")
        lines.append(f"Single-covariate TWFE (state + year FE, clustered SE by state): "
                      f"SE(beta) = {se:.4f}\n")
        lines.append(f"Back-of-envelope MDE (80% power, 5% two-sided test) ~= 2.8 x SE = **{mde:.3f}** "
                      f"percentage points of obesity prevalence per 1-unit increase in "
                      f"GLP-1 prescriptions per 1,000 population.\n")
        sd_treat = df["glp1_per_1000_pop"].std()
        lines.append(f"For context, a one-SD increase in the treatment variable is {sd_treat:.2f} units, "
                      f"so the MDE for a one-SD change in uptake is about {mde*sd_treat:.3f} pp.\n")
    except Exception as exc:  # pragma: no cover
        lines.append(f"Could not estimate (likely insufficient variation at this point): {exc}\n")
    return "\n".join(lines)


TIMING_NOTE = """### 4. Timing note

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
"""


def main() -> None:
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")

    sections = [
        "## Phase 4: Feasibility and power check\n",
        treatment_variation(panel),
        outcome_movement(panel),
        mde_check(panel),
        TIMING_NOTE,
    ]
    content = "\n".join(sections)

    print(content)

    # Written to its own file rather than appended to report/findings.md:
    # findings.md is the hand-assembled final write-up (Phase 10), and this
    # script needs to be safely re-runnable on its own (e.g. after a panel
    # rebuild) without silently mutating or duplicating content in that
    # polished document. The numbers here are copied into findings.md's
    # feasibility section by Phase 10, not auto-injected.
    out_path = config.REPORT_DIR / "feasibility_section.md"
    out_path.write_text(content)
    print(f"\n[feasibility] written to {out_path} (see report/findings.md §3 for the "
          f"version incorporated into the final write-up)")


if __name__ == "__main__":
    main()
