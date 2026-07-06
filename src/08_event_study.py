"""
Phase 7: event study / parallel-trends check.

Since GLP-1RA uptake surged nationally at roughly the same time everywhere
(no staggered treatment timing -- see README), there is no single "treatment
date" per state to build a conventional event-time axis around. Instead we
use a continuous, time-invariant measure of each state's uptake *intensity*
(z-scored 2024 GLP-1 prescriptions per 1,000 population) interacted with
year dummies, omitting 2020 as the base year (the year just before
weight-loss uptake began to scale).

  obesity_pct[s,t] = sum_{y != 2020} theta_y * (z_s * 1[t=y]) + alpha_s + delta_t + eps[s,t]

Pre-2021 theta_y close to zero and statistically insignificant is the
parallel-trends check: it would mean high- and low-uptake states were not
already on different obesity trajectories before treatment intensity existed.
Post-2021 coefficients trace any emerging divergence associated with uptake
intensity. This does not by itself prove causality (see report/findings.md).
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from linearmodels.panel import PanelOLS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from plot_style import CATEGORICAL, INK_MUTED, apply_style

apply_style()

BASE_YEAR = 2020


def build_event_study_frame(panel: pd.DataFrame) -> pd.DataFrame:
    uptake_2024 = panel.loc[panel["year"] == 2024, ["state", "glp1_per_1000_pop"]].set_index("state")
    z = (uptake_2024["glp1_per_1000_pop"] - uptake_2024["glp1_per_1000_pop"].mean()) / \
        uptake_2024["glp1_per_1000_pop"].std()
    df = panel.merge(z.rename("z_uptake"), on="state", how="left")

    for year in config.YEARS:
        if year == BASE_YEAR:
            continue
        df[f"z_x_{year}"] = df["z_uptake"] * (df["year"] == year).astype(float)
    return df


def main() -> None:
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    df = build_event_study_frame(panel)
    df = df.dropna(subset=["obesity_pct", "z_uptake"]).set_index(["state", "year"])

    interaction_cols = [f"z_x_{y}" for y in config.YEARS if y != BASE_YEAR]
    formula = "obesity_pct ~ 1 + " + " + ".join(interaction_cols) + " + EntityEffects + TimeEffects"
    res = PanelOLS.from_formula(formula, data=df).fit(cov_type="clustered", cluster_entity=True)

    coefs, ci_low, ci_high, years = [], [], [], []
    for year in config.YEARS:
        if year == BASE_YEAR:
            coefs.append(0.0); ci_low.append(0.0); ci_high.append(0.0); years.append(year)
            continue
        name = f"z_x_{year}"
        b = res.params[name]
        se = res.std_errors[name]
        coefs.append(b); ci_low.append(b - 1.96 * se); ci_high.append(b + 1.96 * se); years.append(year)

    event_table = pd.DataFrame({"year": years, "coef": coefs, "ci_low": ci_low, "ci_high": ci_high})
    event_table = event_table.sort_values("year")
    out_csv = config.OUTPUTS_TABLES / "event_study.csv"
    event_table.to_csv(out_csv, index=False)
    print(f"[event study] table -> {out_csv}")
    print(event_table.round(4))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        event_table["year"], event_table["coef"],
        yerr=[event_table["coef"] - event_table["ci_low"], event_table["ci_high"] - event_table["coef"]],
        fmt="o", color=CATEGORICAL[0], ecolor=CATEGORICAL[0], elinewidth=1.5, capsize=3, markersize=5,
    )
    ax.axhline(0, color=INK_MUTED, linewidth=0.8)
    ax.axvline(BASE_YEAR, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.set_title("Event study: obesity prevalence and standardized GLP-1 uptake intensity\n"
                 f"(interaction with year, base year = {BASE_YEAR})")
    ax.set_xlabel("Year")
    ax.set_ylabel("Coefficient (pp obesity per 1-SD uptake intensity)")
    fig.tight_layout()
    path = config.OUTPUTS_FIGURES / "event_study.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[event study] figure -> {path}")

    pre = event_table[event_table["year"] < 2021]
    print(f"\nPre-2021 coefficients: mean={pre['coef'].mean():.4f}, "
          f"max abs={pre['coef'].abs().max():.4f} -- "
          f"{'look flat / near zero, consistent with parallel pre-trends' if pre['coef'].abs().max() < 1 else 'show some pre-trend, a caveat for the parallel-trends assumption'}.")


if __name__ == "__main__":
    main()
