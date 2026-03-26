"""
Burch Parshall
Pull monthly solar capacity data from the EIA API v2
for CISO (California ISO) and ERCO (Texas ERCOT).

Data source: https://api.eia.gov/v2/electricity/operating-generator-capacity/
Filters: energy_source_code=SUN, status=OP (operating only)
Aggregates nameplate capacity across all generators per region per month.
"""

import os
import requests
import pandas as pd
import time

API_KEY = os.environ.get("EIA_API_KEY", "")
BASE_URL = "https://api.eia.gov/v2/electricity/operating-generator-capacity/data/"

RESPONDENTS = ["CISO", "ERCO"]
MAX_ROWS = 5000
REQUEST_DELAY = 2
MAX_RETRIES = 10


def fetch_page(offset, start_date, end_date, respondent):
    """Fetch a single page of capacity results from the EIA API."""
    params = {
        "api_key": API_KEY,
        "frequency": "monthly",
        "data[0]": "nameplate-capacity-mw",
        "facets[balancing_authority_code][]": respondent,
        "facets[energy_source_code][]": "SUN",
        "facets[status][]": "OP",
        "start": start_date,
        "end": end_date,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": offset,
        "length": MAX_ROWS,
    }
    for attempt in range(MAX_RETRIES):
        resp = requests.get(BASE_URL, params=params, timeout=60)
        if resp.status_code == 429:
            wait = 60 * (attempt + 1)
            print(f"  Rate limited. Waiting {wait}s before retry {attempt + 1}/{MAX_RETRIES}...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception(f"Failed after {MAX_RETRIES} retries at offset {offset}")


def pull_respondent(respondent, start_date, end_date):
    """Pull all generator-level capacity records for one respondent."""
    print(f"  Pulling capacity for {respondent} from {start_date} to {end_date}...")
    all_records = []
    offset = 0
    while True:
        data = fetch_page(offset, start_date, end_date, respondent)
        total = int(data["response"]["total"])
        records = data["response"]["data"]
        if not records:
            break
        all_records.extend(records)
        offset += MAX_ROWS
        print(f"    Fetched {len(all_records):,} / {total:,}")
        if offset >= total:
            break
        time.sleep(REQUEST_DELAY)
    return all_records


def pull_date_range(start_date, end_date):
    """Pull and aggregate solar capacity for all respondents.

    Args:
        start_date: Start month string (e.g. "2021-01")
        end_date: End month string (e.g. "2026-01")

    Returns:
        DataFrame with columns: respondent_id, date_id, capacity_mw
        One row per respondent per month (first of month).
    """
    all_records = []
    for respondent in RESPONDENTS:
        records = pull_respondent(respondent, start_date, end_date)
        all_records.extend(records)

    if not all_records:
        print("  No capacity records available.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    df["nameplate-capacity-mw"] = pd.to_numeric(df["nameplate-capacity-mw"], errors="coerce")
    df = df.dropna(subset=["period", "balancing_authority_code", "nameplate-capacity-mw"])

    # Aggregate: sum capacity across all generators per region per month
    agg = (
        df.groupby(["balancing_authority_code", "period"])["nameplate-capacity-mw"]
        .sum()
        .reset_index()
    )
    agg.columns = ["respondent_id", "month", "capacity_mw"]

    # Convert month string (e.g. "2021-02") to first-of-month date for date_id FK
    agg["date_id"] = pd.to_datetime(agg["month"] + "-01").dt.date
    agg = agg[["respondent_id", "date_id", "capacity_mw"]]
    agg = agg.sort_values(["respondent_id", "date_id"]).reset_index(drop=True)

    print(f"  Aggregated to {len(agg)} capacity rows ({len(agg) // 2} months x 2 regions).")
    return agg


def main():
    """Pull full capacity dataset and save to CSV."""
    start_date = "2021-01"
    end_date = "2026-01"

    df = pull_date_range(start_date, end_date)
    if df.empty:
        return

    outfile = "eia_capacity_monthly.csv"
    df.to_csv(outfile, index=False)
    print(f"\nSaved {len(df):,} rows to {outfile}")

    print("\n--- Capacity Summary ---")
    print(f"Date range: {df['date_id'].min()} to {df['date_id'].max()}")
    print(f"\nRows per respondent:")
    print(df.groupby("respondent_id")["capacity_mw"].agg(["count", "min", "max"]).to_string())


if __name__ == "__main__":
    main()
