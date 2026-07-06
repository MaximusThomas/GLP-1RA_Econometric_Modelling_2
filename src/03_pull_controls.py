"""
Phase 2c: pull control variables and denominators.

- Medicaid enrollment (denominator for the primary treatment-intensity
  measure, GLP-1 prescriptions per 1,000 enrollees). Only covers 2016-2022;
  documented as a coverage gap, not papered over.
- State population (denominator for the per-capita cross-check measure),
  from two Census PEP vintages stitched together at 2020.
- Age structure (share of population 65+), same two-vintage approach.
- Real personal income per capita and unemployment rate, from FRED.
"""

import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils import get_with_retry, cached_get_text


def pull_medicaid_enrollment() -> pd.DataFrame:
    cache_path = config.DATA_RAW / "medicaid_enrollment.csv"
    text = cached_get_text(cache_path, config.MEDICAID_ENROLLMENT_CSV)
    df = pd.read_csv(StringIO(text))
    df = df[df["ProgramType"] == "Medicaid"].copy()
    df["state"] = df["State"].map(config.STATE_NAME_TO_ABBR)
    df = df.dropna(subset=["state"])
    df["year"] = df["Year"].astype(int)
    enrollment_str = df["AverageEnrollmentPerMonth"].astype(str).str.replace(",", "", regex=False)
    df["medicaid_enrollment"] = pd.to_numeric(enrollment_str, errors="coerce")
    df = df[["state", "year", "medicaid_enrollment"]]
    print(f"[enrollment] {len(df)} rows, years {sorted(df['year'].unique())}")
    return df


def pull_population() -> pd.DataFrame:
    cache1 = config.DATA_RAW / "census_pop_2010_2020.csv"
    cache2 = config.DATA_RAW / "census_pop_2020_2024.csv"
    text1 = cached_get_text(cache1, config.CENSUS_POP_2010_2020)
    text2 = cached_get_text(cache2, config.CENSUS_POP_2020_2024)
    df1 = pd.read_csv(StringIO(text1), dtype={"STATE": str})
    df2 = pd.read_csv(StringIO(text2), dtype={"STATE": str})

    df1 = df1[df1["SUMLEV"] == 40].copy()
    df2 = df2[df2["SUMLEV"] == 40].copy()
    df1["state"] = df1["STATE"].map(config.STATE_FIPS_TO_ABBR)
    df2["state"] = df2["STATE"].map(config.STATE_FIPS_TO_ABBR)
    df1 = df1.dropna(subset=["state"])
    df2 = df2.dropna(subset=["state"])

    rows = []
    # 2011-2019 from the 2010-2020 vintage; 2020-2024 from the 2020-2024
    # vintage (avoids mixing two different post-2020-census rebasings).
    for year in config.YEARS:
        col = f"POPESTIMATE{year}"
        src = df1 if year < 2020 else df2
        if col not in src.columns:
            continue
        for _, row in src.iterrows():
            rows.append({"state": row["state"], "year": year, "population": row[col]})
    pop = pd.DataFrame(rows)
    print(f"[population] {len(pop)} rows, years {sorted(pop['year'].unique())}")
    return pop


def pull_age_structure() -> pd.DataFrame:
    cache1 = config.DATA_RAW / "census_age_2010_2020.csv"
    cache2 = config.DATA_RAW / "census_age_2020_2024.csv"
    text1 = cached_get_text(cache1, config.CENSUS_AGE_2010_2020)
    text2 = cached_get_text(cache2, config.CENSUS_AGE_2020_2024)
    df1 = pd.read_csv(StringIO(text1), dtype={"STATE": str})
    df2 = pd.read_csv(StringIO(text2), dtype={"STATE": str})

    def extract(df, suffix, years):
        df = df[df["SEX"] == 0].copy()
        df["state"] = df["STATE"].str.zfill(2).map(config.STATE_FIPS_TO_ABBR)
        df = df.dropna(subset=["state"])
        out = []
        for year in years:
            col = f"POPEST{year}_{suffix}"
            if col not in df.columns:
                continue
            total = df[df["AGE"] == 999].set_index("state")[col]
            age65 = df[(df["AGE"] >= 65) & (df["AGE"] <= 85)].groupby("state")[col].sum()
            for state in total.index:
                out.append({
                    "state": state, "year": year,
                    "pct_65plus": 100 * age65.get(state, float("nan")) / total[state],
                })
        return pd.DataFrame(out)

    years1 = [y for y in config.YEARS if y < 2020]
    years2 = [y for y in config.YEARS if y >= 2020]
    part1 = extract(df1, "CIV", years1)
    part2 = extract(df2, "CIV", years2)
    age = pd.concat([part1, part2], ignore_index=True)
    print(f"[age structure] {len(age)} rows, years {sorted(age['year'].unique())}")
    return age


def fetch_fred_series(series_id: str) -> pd.DataFrame:
    params = {
        "series_id": series_id,
        "file_type": "json",
        "api_key": config.FRED_API_KEY,
        "observation_start": f"{config.YEAR_START}-01-01",
        "observation_end": f"{config.YEAR_END}-12-31",
    }
    resp = get_with_retry(config.FRED_API_ENDPOINT, params=params)
    obs = resp.json().get("observations", [])
    df = pd.DataFrame(obs)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["year", "value"]]


def pull_fred_controls() -> pd.DataFrame:
    cache_path = config.DATA_RAW / "fred_controls.csv"
    if cache_path.exists():
        print(f"[fred] using cached {cache_path}")
        return pd.read_csv(cache_path)

    if not config.FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is not set (checked .env and environment). "
            "Cannot pull income/unemployment controls without it."
        )

    print("[fred] pulling CPI deflator...")
    cpi = fetch_fred_series(config.FRED_CPI_SERIES)
    cpi_annual = cpi.groupby("year")["value"].mean()
    base_cpi = cpi_annual.loc[config.YEAR_END]

    rows = []
    for state in config.STATE_ABBRS:
        pcpi = fetch_fred_series(config.fred_pcpi_series(state))
        ur = fetch_fred_series(config.fred_unemployment_series(state))
        ur_annual = ur.groupby("year")["value"].mean()
        pcpi_by_year = pcpi.set_index("year")["value"]
        for year in config.YEARS:
            nominal = pcpi_by_year.get(year, float("nan"))
            real = nominal * (base_cpi / cpi_annual.get(year, float("nan"))) if pd.notna(nominal) else float("nan")
            rows.append({
                "state": state, "year": year,
                "income_pc_nominal": nominal,
                "income_pc_real": real,
                "unemployment_rate": ur_annual.get(year, float("nan")),
            })
        time.sleep(0.05)

    df = pd.DataFrame(rows)
    df.to_csv(cache_path, index=False)
    print(f"[fred] cached {len(df)} rows to {cache_path}")
    return df


if __name__ == "__main__":
    enrollment = pull_medicaid_enrollment()
    population = pull_population()
    age = pull_age_structure()
    fred = pull_fred_controls()

    # Save cleaned, analysis-ready versions (distinct from the raw source
    # CSVs cached above) so 04_build_panel.py can just read these directly.
    enrollment.to_csv(config.DATA_RAW / "medicaid_enrollment_clean.csv", index=False)
    population.to_csv(config.DATA_RAW / "population_clean.csv", index=False)
    age.to_csv(config.DATA_RAW / "age_structure_clean.csv", index=False)

    for name, df, col in [
        ("Medicaid enrollment", enrollment, "medicaid_enrollment"),
        ("Population", population, "population"),
        ("Age structure (% 65+)", age, "pct_65plus"),
        ("FRED income (real)", fred, "income_pc_real"),
        ("FRED unemployment", fred, "unemployment_rate"),
    ]:
        years = sorted(df["year"].unique())
        states = sorted(df["state"].unique())
        missing_states = sorted(set(config.STATE_ABBRS) - set(states))
        print(f"\n=== {name} coverage ===")
        print(f"Rows: {len(df)}, years: {years[0] if years else None}-{years[-1] if years else None}, "
              f"states: {len(states)}/{config.N_STATES}")
        if missing_states:
            print(f"Missing states: {missing_states}")
        print(df[col].describe())
