"""
Phase 5: descriptive statistics and figures.

Produces:
  - outputs/tables/summary_stats.csv: mean/SD/min/max/N for every panel variable.
  - outputs/figures/trend_obesity.png: national (unweighted mean across states)
    obesity trend, 2011-2024.
  - outputs/figures/trend_glp1_uptake.png: national GLP-1 uptake trend.
    (Two separate figures, not one dual-axis chart -- obesity (%) and uptake
    (prescriptions per 1,000) are different scales/units.)
  - outputs/figures/scatter_delta.png: state-level scatter of the change in
    obesity vs. change in GLP-1 uptake over the post-period.
  - outputs/figures/state_trajectories.png: obesity trends for a few example
    high- vs. low-uptake states.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from plot_style import CATEGORICAL, INK_MUTED, apply_style

apply_style()


def summary_stats(panel: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = panel.select_dtypes("number").columns.drop(["year"], errors="ignore")
    stats = panel[numeric_cols].agg(["mean", "std", "min", "max", "count"]).T
    stats = stats.rename(columns={"count": "N"})
    out_path = config.OUTPUTS_TABLES / "summary_stats.csv"
    stats.to_csv(out_path)
    print(f"[descriptives] summary stats -> {out_path}")
    print(stats.round(2))
    return stats


def plot_obesity_trend(panel: pd.DataFrame) -> None:
    trend = panel.groupby("year")["obesity_pct"].mean()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(trend.index, trend.values, color=CATEGORICAL[0], marker="o", markersize=5)
    ax.set_title("National adult obesity prevalence, 2011-2024")
    ax.set_ylabel("Obesity prevalence (%, unweighted mean across states)")
    ax.set_xlabel("Year")
    ax.axvline(2021, color=INK_MUTED, linestyle="--", linewidth=1)
    ax.text(2021.1, trend.min(), "GLP-1 weight-loss uptake begins to scale", fontsize=8, color=INK_MUTED)
    fig.tight_layout()
    path = config.OUTPUTS_FIGURES / "trend_obesity.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[descriptives] figure -> {path}")


def plot_glp1_trend(panel: pd.DataFrame) -> None:
    trend = panel.groupby("year")["glp1_per_1000_pop"].mean()
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(trend.index, trend.values, color=CATEGORICAL[1], marker="o", markersize=5)
    ax.set_title("National GLP-1RA uptake (Medicaid), 2011-2024")
    ax.set_ylabel("GLP-1 prescriptions per 1,000 population")
    ax.set_xlabel("Year")
    fig.tight_layout()
    path = config.OUTPUTS_FIGURES / "trend_glp1_uptake.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[descriptives] figure -> {path}")


def plot_scatter_delta(panel: pd.DataFrame, year_from: int = 2019, year_to: int = 2024) -> None:
    wide_ob = panel.pivot(index="state", columns="year", values="obesity_pct")
    wide_up = panel.pivot(index="state", columns="year", values="glp1_per_1000_pop")
    d_ob = wide_ob[year_to] - wide_ob[year_from]
    d_up = wide_up[year_to] - wide_up[year_from]
    data = pd.DataFrame({"d_obesity": d_ob, "d_uptake": d_up}).dropna()

    fig, ax = plt.subplots(figsize=(6, 5.5))
    ax.scatter(data["d_uptake"], data["d_obesity"], color=CATEGORICAL[0], s=40, alpha=0.8, edgecolor="white")
    for state, row in data.iterrows():
        ax.annotate(state, (row["d_uptake"], row["d_obesity"]), fontsize=6.5, color=INK_MUTED,
                    xytext=(3, 3), textcoords="offset points")
    ax.set_title(f"State-level change, {year_from}-{year_to}")
    ax.set_xlabel("Change in GLP-1 prescriptions per 1,000 population")
    ax.set_ylabel("Change in obesity prevalence (pp)")
    ax.axhline(0, color=INK_MUTED, linewidth=0.8)
    fig.tight_layout()
    path = config.OUTPUTS_FIGURES / "scatter_delta.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[descriptives] figure -> {path}")


def plot_state_trajectories(panel: pd.DataFrame, year_for_ranking: int = 2024) -> None:
    uptake_rank = panel[panel["year"] == year_for_ranking].set_index("state")["glp1_per_1000_pop"].sort_values()
    uptake_rank = uptake_rank.dropna()
    picks = [uptake_rank.index[0], uptake_rank.index[len(uptake_rank) // 2], uptake_rank.index[-1]]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for i, state in enumerate(picks):
        series = panel[panel["state"] == state].set_index("year")["obesity_pct"]
        label = f"{state} ({'lowest' if i == 0 else 'median' if i == 1 else 'highest'} 2024 uptake)"
        ax.plot(series.index, series.values, color=CATEGORICAL[i], marker="o", markersize=4, label=label)
    ax.set_title("Example state obesity trajectories, by 2024 GLP-1 uptake rank")
    ax.set_ylabel("Obesity prevalence (%)")
    ax.set_xlabel("Year")
    ax.legend(fontsize=8, frameon=False)
    fig.tight_layout()
    path = config.OUTPUTS_FIGURES / "state_trajectories.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[descriptives] figure -> {path}")


if __name__ == "__main__":
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv")
    summary_stats(panel)
    plot_obesity_trend(panel)
    plot_glp1_trend(panel)
    plot_scatter_delta(panel)
    plot_state_trajectories(panel)
