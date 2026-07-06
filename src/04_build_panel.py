"""
Phase 3: build the state x year analysis panel.

Combines:
  - outcome:    BRFSS obesity prevalence (+ USDSS diabetes as secondary outcome)
  - treatment:  Medicaid SDUD GLP-1 prescriptions, aggregated to state-year
  - controls:   Medicaid enrollment, population, age structure, FRED income/unemployment

into one balanced state x year panel, 2011-2024 (51 states x 14 years = 714 rows).

Suppression handling (SDUD): CMS suppresses any state-quarter-NDC-utilization_type
cell with fewer than 11 prescriptions, for privacy. The true value is somewhere in
1-10. Primary rule here: impute suppressed cells as 5 (the midpoint) before summing
to state-year. This is a judgement call, not a fact -- 09_robustness.py re-runs the
main specification with 0 and 10 as alternative imputed values to check sensitivity.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

SUPPRESSED_IMPUTATION_VALUE = 5  # primary rule; see module docstring


def load_sdud_raw() -> pd.DataFrame:
    frames = []
    missing_years = []
    for year in config.YEARS:
        path = config.DATA_RAW / f"sdud_glp1_{year}.csv"
        if not path.exists():
            missing_years.append(year)
            continue
        frames.append(pd.read_csv(path))
    if missing_years:
        print(f"[panel] WARNING: SDUD raw pull missing for years {missing_years} "
              f"(run 02_pull_glp1.py first) -- proceeding with what is available.")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def aggregate_sdud_to_state_year(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["is_suppressed"] = df["suppression_used"].astype(str).str.lower() == "true"
    df["number_of_prescriptions"] = pd.to_numeric(df["number_of_prescriptions"], errors="coerce")
    df["rx_imputed"] = np.where(
        df["is_suppressed"], SUPPRESSED_IMPUTATION_VALUE, df["number_of_prescriptions"].fillna(0)
    )

    agg = df.groupby(["state", "year"]).agg(
        glp1_prescriptions=("rx_imputed", "sum"),
        n_cells=("rx_imputed", "size"),
        n_suppressed_cells=("is_suppressed", "sum"),
    ).reset_index()
    agg["pct_cells_suppressed"] = 100 * agg["n_suppressed_cells"] / agg["n_cells"]
    return agg


def build_skeleton() -> pd.DataFrame:
    """Every (state, year) combination -- the target balanced panel shape."""
    return pd.DataFrame(
        [(s, y) for s in config.STATE_ABBRS for y in config.YEARS],
        columns=["state", "year"],
    )


def main() -> None:
    skeleton = build_skeleton()
    print(f"[panel] skeleton: {len(skeleton)} rows ({config.N_STATES} states x {len(config.YEARS)} years)")

    obesity = pd.read_csv(config.DATA_RAW / "brfss_obesity.csv")
    diabetes = pd.read_csv(config.DATA_RAW / "usdss_diabetes.csv")
    enrollment = pd.read_csv(config.DATA_RAW / "medicaid_enrollment_clean.csv")
    population = pd.read_csv(config.DATA_RAW / "population_clean.csv")
    age = pd.read_csv(config.DATA_RAW / "age_structure_clean.csv")
    fred = pd.read_csv(config.DATA_RAW / "fred_controls.csv")

    sdud_raw = load_sdud_raw()
    treatment = aggregate_sdud_to_state_year(sdud_raw) if len(sdud_raw) else pd.DataFrame(
        columns=["state", "year", "glp1_prescriptions", "n_cells", "n_suppressed_cells", "pct_cells_suppressed"]
    )

    panel = skeleton.copy()
    for name, df in [
        ("obesity", obesity), ("diabetes", diabetes), ("treatment", treatment),
        ("enrollment", enrollment), ("population", population),
        ("age", age), ("fred", fred),
    ]:
        before = len(panel)
        panel = panel.merge(df, on=["state", "year"], how="left")
        assert len(panel) == before, f"merge with {name} changed row count -- duplicate keys in source"

    # A state-year with zero raw SDUD rows (no GLP-1 records at all -- e.g.
    # ME 2020) is a genuine zero, not a missing value, so fill before
    # computing ratios (otherwise 0/population would wrongly become NaN).
    panel["glp1_prescriptions"] = panel["glp1_prescriptions"].fillna(0)

    # Treatment intensity measures.
    # Primary: per 1,000 Medicaid enrollees (only defined 2016-2022, the
    # enrollment series' coverage window -- see README for why).
    panel["glp1_per_1000_enrollees"] = 1000 * panel["glp1_prescriptions"] / panel["medicaid_enrollment"]
    # Secondary/cross-check: per 1,000 total state population (full 2011-2024
    # coverage), since SDUD's numerator is Medicaid-only but the denominator
    # here is not, this is a cross-check on relative uptake, not a rate.
    panel["glp1_per_1000_pop"] = 1000 * panel["glp1_prescriptions"] / panel["population"]

    panel["log_income_pc"] = np.log(panel["income_pc_real"])
    panel["log_population"] = np.log(panel["population"])

    out_path = config.DATA_PROCESSED / "panel.csv"
    panel.to_csv(out_path, index=False)

    print(f"\n[panel] final panel: {len(panel)} rows, {panel['state'].nunique()} states, "
          f"{panel['year'].nunique()} years -> saved to {out_path}")
    print("\nMissingness by column (count of NaN out of", len(panel), "rows):")
    print(panel.isna().sum().sort_values(ascending=False))

    print("\nSample:")
    print(panel.head())

    print("\nSuppression summary (share of SDUD cells suppressed, by year):")
    if len(treatment):
        print(panel.groupby("year")["pct_cells_suppressed"].mean())


if __name__ == "__main__":
    main()
