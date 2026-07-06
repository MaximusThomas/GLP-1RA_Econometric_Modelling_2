"""
Phase 2b: pull the treatment variable -- GLP-1RA prescription counts.

Source: Medicaid State Drug Utilization Data (SDUD), one dataset per year
on data.medicaid.gov (a DKAN datastore API, not Socrata, despite the
similar query-string style). For each year we query once per GLP-1 product
name (brand + molecule), paginating with limit/offset, then concatenate
and de-duplicate. Each year's raw pull is cached separately so a partial
run can resume without re-hitting already-fetched years.
"""

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from utils import get_with_retry

PAGE_LIMIT = 5000
FIELDS = [
    "utilization_type", "state", "ndc", "product_name", "year", "quarter",
    "suppression_used", "units_reimbursed", "number_of_prescriptions",
    "total_amount_reimbursed",
]


def query_product(dataset_id: str, product: str) -> pd.DataFrame:
    """Pull all SDUD rows for one product (LIKE match), paginating as needed."""
    url = config.SDUD_QUERY_TEMPLATE.format(dataset_id=dataset_id)
    rows = []
    offset = 0
    while True:
        params = {
            "conditions[0][property]": "product_name",
            "conditions[0][value]": f"%{product}%",
            "conditions[0][operator]": "like",
            "limit": PAGE_LIMIT,
            "offset": offset,
        }
        resp = get_with_retry(url, params=params)
        payload = resp.json()
        batch = payload.get("results", [])
        rows.extend(batch)
        count = payload.get("count", len(batch))
        offset += PAGE_LIMIT
        if offset >= count or not batch:
            break
    return pd.DataFrame(rows)


def pull_year(year: int) -> pd.DataFrame:
    cache_path = config.DATA_RAW / f"sdud_glp1_{year}.csv"
    if cache_path.exists():
        print(f"[sdud {year}] using cached {cache_path}")
        return pd.read_csv(cache_path)

    dataset_id = config.SDUD_DATASET_IDS[year]
    print(f"[sdud {year}] querying dataset {dataset_id} for {len(config.GLP1_PRODUCTS)} products...")
    frames = []
    for product in config.GLP1_PRODUCTS:
        df = query_product(dataset_id, product)
        if len(df):
            frames.append(df)
        time.sleep(0.1)  # be polite to the API

    if not frames:
        year_df = pd.DataFrame(columns=FIELDS)
    else:
        year_df = pd.concat(frames, ignore_index=True)
        year_df = year_df[FIELDS].drop_duplicates()

    year_df.to_csv(cache_path, index=False)
    print(f"[sdud {year}] cached {len(year_df)} raw rows to {cache_path}")
    return year_df


def report_coverage(df: pd.DataFrame) -> None:
    years = sorted(df["year"].unique())
    states = sorted(df["state"].unique())
    missing_states = sorted(set(config.STATE_ABBRS) - set(states))

    print("\n=== SDUD GLP-1 raw pull coverage ===")
    print(f"Total raw rows (state x quarter x NDC x utilization_type): {len(df)}")
    print(f"Years covered: {years}")
    print(f"States with >=1 GLP-1 record: {len(states)} / {config.N_STATES}")
    if missing_states:
        print(f"States with zero GLP-1 records in the whole panel: {missing_states}")
    print("\nRows per year:")
    print(df.groupby("year").size())
    print("\nSuppressed rows per year (suppression_used == True):")
    df["suppression_used"] = df["suppression_used"].astype(str).str.lower() == "true"
    print(df.groupby("year")["suppression_used"].sum())
    print("\nTop products by row count:")
    print(df["product_name"].str.strip().value_counts().head(20))


if __name__ == "__main__":
    all_years = []
    for year in config.YEARS:
        all_years.append(pull_year(year))
    combined = pd.concat(all_years, ignore_index=True)
    report_coverage(combined)
