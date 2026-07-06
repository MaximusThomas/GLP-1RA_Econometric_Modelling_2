"""
Phase 2a: pull the outcome variables.

Primary outcome: adult obesity prevalence by state-year, from the CDC BRFSS
(Behavioral Risk Factor Surveillance System), via the Socrata API on
chronicdata.cdc.gov.

Secondary outcome (for robustness, Phase 8): diagnosed diabetes prevalence
by state-year, from the CDC's US Diabetes Surveillance System (USDSS), via
the Socrata API on data.cdc.gov. GLP-1RAs are heavily prescribed for
diabetes, so this is a natural secondary outcome to check.

Both are cached to data/raw/ as CSV so re-running this script doesn't
re-hit the API.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils import get_with_retry


def pull_brfss_obesity() -> pd.DataFrame:
    cache_path = config.DATA_RAW / "brfss_obesity.csv"
    if cache_path.exists():
        print(f"[obesity] using cached {cache_path}")
        return pd.read_csv(cache_path)

    print("[obesity] querying CDC BRFSS (chronicdata.cdc.gov, dataset hn4x-zwk7)...")
    where_clause = (
        f"stratificationcategory1='Total' AND question='{config.BRFSS_OBESITY_QUESTION}' "
        f"AND yearstart >= '{config.YEAR_START}' AND yearstart <= '{config.YEAR_END}'"
    )
    params = {
        "$where": where_clause,
        "$select": "yearstart,locationabbr,locationdesc,data_value,"
                    "low_confidence_limit,high_confidence_limit,sample_size",
        "$limit": 5000,
    }
    resp = get_with_retry(config.BRFSS_OBESITY_ENDPOINT, params=params)
    df = pd.DataFrame(resp.json())
    df = df.rename(columns={
        "yearstart": "year",
        "locationabbr": "state",
        "data_value": "obesity_pct",
        "low_confidence_limit": "obesity_ci_low",
        "high_confidence_limit": "obesity_ci_high",
    })
    df["year"] = df["year"].astype(int)
    for c in ("obesity_pct", "obesity_ci_low", "obesity_ci_high", "sample_size"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Keep only the 50 states + DC (drops US aggregate, territories like PR/GU).
    df = df[df["state"].isin(config.STATE_ABBRS)].reset_index(drop=True)
    df = df[["state", "year", "obesity_pct", "obesity_ci_low", "obesity_ci_high", "sample_size"]]
    df.to_csv(cache_path, index=False)
    print(f"[obesity] cached {len(df)} rows to {cache_path}")
    return df


def pull_usdss_diabetes() -> pd.DataFrame:
    cache_path = config.DATA_RAW / "usdss_diabetes.csv"
    if cache_path.exists():
        print(f"[diabetes] using cached {cache_path}")
        return pd.read_csv(cache_path)

    print("[diabetes] querying CDC USDSS (data.cdc.gov, dataset b559-sbez)...")
    where_clause = (
        f"indicator='{config.USDSS_DIABETES_INDICATOR}' AND unit='Percentage' "
        f"AND age='Crude' AND race='All' AND sex='All' AND education='All' "
        f"AND year >= '{config.YEAR_START}' AND year <= '{config.YEAR_END}'"
    )
    params = {
        "$where": where_clause,
        "$select": "state,year,estimate,lowerlimit,upperlimit",
        "$limit": 5000,
    }
    resp = get_with_retry(config.USDSS_DIABETES_ENDPOINT, params=params)
    df = pd.DataFrame(resp.json())
    df = df.rename(columns={
        "estimate": "diabetes_pct",
        "lowerlimit": "diabetes_ci_low",
        "upperlimit": "diabetes_ci_high",
    })
    df["year"] = df["year"].astype(int)
    for c in ("diabetes_pct", "diabetes_ci_low", "diabetes_ci_high"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df[df["state"].isin(config.STATE_ABBRS)].reset_index(drop=True)
    df = df[["state", "year", "diabetes_pct", "diabetes_ci_low", "diabetes_ci_high"]]
    df.to_csv(cache_path, index=False)
    print(f"[diabetes] cached {len(df)} rows to {cache_path}")
    return df


def report_coverage(df: pd.DataFrame, name: str, value_col: str) -> None:
    years = sorted(df["year"].unique())
    states = sorted(df["state"].unique())
    missing_states = sorted(set(config.STATE_ABBRS) - set(states))
    expected = config.N_STATES * len(config.YEARS)

    print(f"\n=== {name} coverage ===")
    print(f"Rows: {len(df)} (expected up to {expected} for {config.N_STATES} states x {len(config.YEARS)} years)")
    print(f"Years covered: {years[0]}-{years[-1]} ({len(years)} years)")
    print(f"States covered: {len(states)} / {config.N_STATES}")
    if missing_states:
        print(f"Missing states entirely: {missing_states}")
    missing_year_state = []
    for y in config.YEARS:
        have = set(df.loc[df["year"] == y, "state"])
        miss = set(config.STATE_ABBRS) - have
        if miss:
            missing_year_state.append((y, sorted(miss)))
    if missing_year_state:
        print("Missing (year, states) cells:")
        for y, miss in missing_year_state:
            print(f"  {y}: {miss}")
    else:
        print("No missing state-year cells.")
    print(df.head())
    print(df[value_col].describe())


if __name__ == "__main__":
    obesity = pull_brfss_obesity()
    report_coverage(obesity, "BRFSS obesity", "obesity_pct")

    diabetes = pull_usdss_diabetes()
    report_coverage(diabetes, "USDSS diabetes", "diabetes_pct")
