"""
Project-wide constants for the GLP-1RA / obesity econometrics project.

Every data-pulling script (src/01-03) imports from here so that the
year range, state list, and endpoint URLs are defined in exactly one place.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS_FIGURES = ROOT / "outputs" / "figures"
OUTPUTS_TABLES = ROOT / "outputs" / "tables"
REPORT_DIR = ROOT / "report"

for d in (DATA_RAW, DATA_PROCESSED, OUTPUTS_FIGURES, OUTPUTS_TABLES, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

# --------------------------------------------------------------------------
# Panel dimensions
# --------------------------------------------------------------------------
# BRFSS obesity prevalence is only methodologically consistent from 2011
# onward (landline+cellphone weighting change) -- see project brief section 2a.
YEAR_START = 2011
YEAR_END = 2024
YEARS = list(range(YEAR_START, YEAR_END + 1))

# 50 states + DC. Postal abbreviation -> (full name, 2-digit FIPS code).
# FIPS codes are needed to build BLS LAUS series IDs.
STATES = {
    "AL": ("Alabama", "01"), "AK": ("Alaska", "02"), "AZ": ("Arizona", "04"),
    "AR": ("Arkansas", "05"), "CA": ("California", "06"), "CO": ("Colorado", "08"),
    "CT": ("Connecticut", "09"), "DE": ("Delaware", "10"), "DC": ("District of Columbia", "11"),
    "FL": ("Florida", "12"), "GA": ("Georgia", "13"), "HI": ("Hawaii", "15"),
    "ID": ("Idaho", "16"), "IL": ("Illinois", "17"), "IN": ("Indiana", "18"),
    "IA": ("Iowa", "19"), "KS": ("Kansas", "20"), "KY": ("Kentucky", "21"),
    "LA": ("Louisiana", "22"), "ME": ("Maine", "23"), "MD": ("Maryland", "24"),
    "MA": ("Massachusetts", "25"), "MI": ("Michigan", "26"), "MN": ("Minnesota", "27"),
    "MS": ("Mississippi", "28"), "MO": ("Missouri", "29"), "MT": ("Montana", "30"),
    "NE": ("Nebraska", "31"), "NV": ("Nevada", "32"), "NH": ("New Hampshire", "33"),
    "NJ": ("New Jersey", "34"), "NM": ("New Mexico", "35"), "NY": ("New York", "36"),
    "NC": ("North Carolina", "37"), "ND": ("North Dakota", "38"), "OH": ("Ohio", "39"),
    "OK": ("Oklahoma", "40"), "OR": ("Oregon", "41"), "PA": ("Pennsylvania", "42"),
    "RI": ("Rhode Island", "44"), "SC": ("South Carolina", "45"), "SD": ("South Dakota", "46"),
    "TN": ("Tennessee", "47"), "TX": ("Texas", "48"), "UT": ("Utah", "49"),
    "VT": ("Vermont", "50"), "VA": ("Virginia", "51"), "WA": ("Washington", "53"),
    "WV": ("West Virginia", "54"), "WI": ("Wisconsin", "55"), "WY": ("Wyoming", "56"),
}
STATE_ABBRS = list(STATES.keys())
STATE_NAME_TO_ABBR = {v[0]: k for k, v in STATES.items()}
STATE_FIPS_TO_ABBR = {v[1]: k for k, v in STATES.items()}

N_STATES = len(STATES)  # 51 (50 states + DC)

# --------------------------------------------------------------------------
# GLP-1 receptor agonist product list (brand names as they appear in SDUD
# `product_name`; matched case-insensitively with a LIKE/contains filter).
# Molecule names are included too in case a state reports generically.
# --------------------------------------------------------------------------
GLP1_PRODUCTS = [
    "OZEMPIC", "WEGOVY", "RYBELSUS",       # semaglutide
    "MOUNJARO", "ZEPBOUND",                # tirzepatide
    "TRULICITY",                            # dulaglutide
    "VICTOZA", "SAXENDA",                   # liraglutide
    "BYETTA", "BYDUREON",                   # exenatide
    "ADLYXIN",                              # lixisenatide
    "TANZEUM",                              # albiglutide
    "SEMAGLUTIDE", "TIRZEPATIDE", "DULAGLUTIDE",
    "LIRAGLUTIDE", "EXENATIDE", "LIXISENATIDE", "ALBIGLUTIDE",
]

# --------------------------------------------------------------------------
# Data source endpoints
# All verified live during Phase 1 scaffolding (2026-07-05). Socrata/DKAN
# dataset IDs are the actual current IDs, not guesses -- see README for how
# to re-verify if a source changes.
# --------------------------------------------------------------------------

# 2a. Outcome: CDC BRFSS obesity prevalence (Socrata, chronicdata.cdc.gov)
# Dataset: "Nutrition, Physical Activity, and Obesity - BRFSS"
BRFSS_OBESITY_ENDPOINT = "https://chronicdata.cdc.gov/resource/hn4x-zwk7.json"
BRFSS_OBESITY_QUESTION = "Percent of adults aged 18 years and older who have obesity"

# 2a (secondary outcome): CDC US Diabetes Surveillance System (USDSS)
# Dataset: "USDSS State Burden/Magnitude Diabetes Indicators"
USDSS_DIABETES_ENDPOINT = "https://data.cdc.gov/resource/b559-sbez.json"
USDSS_DIABETES_INDICATOR = "Diagnosed Diabetes"

# 2b. Treatment: Medicaid State Drug Utilization Data (SDUD), one dataset
# per year on data.medicaid.gov (DKAN datastore API). Verified via
# https://data.medicaid.gov/api/1/search?fulltext=State+Drug+Utilization+Data
SDUD_DATASET_IDS = {
    2011: "138872f1-b1ba-5e05-be13-8be200306a58",
    2012: "992936b2-2a72-5df6-a734-a56a8631b87a",
    2013: "6a91f80f-e2fd-5f43-8e38-afcebebb8387",
    2014: "a9cfe5e9-d7d8-5b87-a7db-b45a7daf84fc",
    2015: "2fed5758-5fd6-5dbb-8f92-34b3a0c3c8dd",
    2016: "53cf9f05-97e3-5bd6-a237-bc971e3642d9",
    2017: "776a3880-a62d-5990-8b40-4406e6861dbb",
    2018: "a1f3598e-fc71-51aa-8560-78e7e1a61b09",
    2019: "daba7980-e219-5996-9bec-90358fd156f1",
    2020: "cc318bfb-a9b2-55f3-a924-d47376b32ea3",
    2021: "eec7fbe6-c4c4-5915-b3d0-be5828ef4e9d",
    2022: "200c2cba-e58d-4a95-aa60-14b99736808d",
    2023: "d890d3a9-6b00-43fd-8b31-fcba4c8e2909",
    2024: "61729e5a-7aa8-448c-8903-ba3e0cd0ea3c",
}
SDUD_QUERY_TEMPLATE = "https://data.medicaid.gov/api/1/datastore/query/{dataset_id}/0"

# 2c. Controls
# Medicaid enrollment (average monthly enrollment, by state/year/program type).
# NOTE: only covers 2016-2022 -- a genuine coverage gap, documented in Phase 4/9.
MEDICAID_ENROLLMENT_CSV = "https://download.medicaid.gov/data/ProgramType-anul.csv"

# Census Population Estimates Program (PEP), bulk CSV (no API key required).
# Two vintages stitched together at 2020 (see 04_build_panel.py for the join).
CENSUS_POP_2010_2020 = "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/state/totals/nst-est2020-alldata.csv"
CENSUS_POP_2020_2024 = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/totals/NST-EST2024-ALLDATA.csv"

# Census age structure (65+ share, median age), bulk CSV, no API key.
CENSUS_AGE_2010_2020 = "https://www2.census.gov/programs-surveys/popest/datasets/2010-2020/state/asrh/PRC-EST2020-AGESEX.csv"
CENSUS_AGE_2020_2024 = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/state/asrh/sc-est2024-agesex-civ.csv"

# BLS LAUS state unemployment rate (public API v2, keyless at this request
# volume: 25 series/day limit applies without a registered key -- we query
# all 51 states in state-sized batches with a pause between batches).
# Series ID pattern: LASST + 2-digit FIPS + 0000000000 + 03 (unemployment rate).
BLS_API_ENDPOINT = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

def bls_series_id(fips: str) -> str:
    return f"LASST{fips}0000000000003"

# Census SAIPE median household income, per-state fixed-width text files
# (no API key). Record layout confirmed from:
# https://www2.census.gov/programs-surveys/saipe/technical-documentation/file-layouts/state-county/2019-estimate-layout.txt
# Median household income estimate occupies characters 134-139 (1-indexed).
SAIPE_MHI_COLSPEC = (133, 139)  # 0-indexed, end-exclusive

def saipe_url(year: int, state_abbr: str) -> str:
    yy = f"{year % 100:02d}"
    return (
        f"https://www2.census.gov/programs-surveys/saipe/datasets/{year}/"
        f"{year}-state-and-county/est{yy}-{state_abbr.lower()}.txt"
    )

# --------------------------------------------------------------------------
# FRED substitution note (see README / report/findings.md for full writeup):
# The project brief specifies FRED for real personal income per capita and
# unemployment rate. FRED requires a free API key that needs a human to
# register; none was available in this run. Substitutes used instead,
# documented here so the choice is explicit and reproducible:
#   - Unemployment rate:  BLS LAUS public API (keyless) instead of FRED.
#   - Income:             Census SAIPE median household income (keyless)
#                          instead of FRED real personal income per capita.
#                          This is a household-income concept, not per-capita
#                          personal income -- noted as a limitation.
# If a FRED key becomes available, swap these two sources for the FRED
# series and re-run 03_pull_controls.py; the rest of the pipeline is
# agnostic to which source populated `unemployment_rate` / `log_income_pc`.
# --------------------------------------------------------------------------
