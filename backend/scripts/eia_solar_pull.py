"""
Sanbir Rahman
Pull hourly solar generation data from the EIA API v2
for CISO (California ISO) and ERCO (Texas ERCOT).

Data source: https://api.eia.gov/v2/electricity/rto/fuel-type-data/
Fuel type: SUN (Solar)
"""

import os
import requests
import pandas as pd
import time
from datetime import datetime

API_KEY = os.environ.get("EIA_API_KEY", "")
BASE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"

RESPONDENTS = ["CISO", "ERCO"]
FUEL_TYPE = "SUN"
MAX_ROWS = 5000
REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 10


def fetch_page(offset, start_date, end_date):
    """Fetch a single page of results from the EIA API with retry on 429."""
    params = {
        "api_key": API_KEY,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": RESPONDENTS,
        "facets[fueltype][]": FUEL_TYPE,
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


def clean(df):
    """Apply cleaning: type conversion, dedup, null handling, negative fix."""
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["period"] = pd.to_datetime(df["period"], errors="coerce")

    # Filter to only solar fuel type
    df = df[df["fueltype"] == FUEL_TYPE].copy()

    # Drop rows missing key fields
    df = df.dropna(subset=["period", "respondent", "value"])
    df = df[df["respondent"].isin(RESPONDENTS)].copy()

    # Remove duplicate observations
    df = df.drop_duplicates(subset=["respondent", "period"])

    # Fix negative solar values sometimes returned by EIA
    df.loc[df["value"] < 0, "value"] = 0

    df.sort_values(["respondent", "period"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def pull_date_range(start_date, end_date):
    """Pull and clean EIA solar data for a date range.

    Args:
        start_date: Start datetime string (e.g. "2026-03-16T00")
        end_date: End datetime string (e.g. "2026-03-24T00")

    Returns:
        Cleaned DataFrame with columns: respondent, period, value
    """
    print(f"  Pulling EIA solar from {start_date} to {end_date}...")

    all_records = []
    offset = 0
    while True:
        data = fetch_page(offset, start_date, end_date)
        total = int(data["response"]["total"])
        records = data["response"]["data"]
        if not records:
            break
        all_records.extend(records)
        offset += MAX_ROWS
        print(f"  Fetched {len(all_records):,} / {total:,}")
        if offset >= total:
            break
        time.sleep(REQUEST_DELAY)

    if not all_records:
        print("  No records available.")
        return pd.DataFrame()

    df = pd.DataFrame(all_records)
    return clean(df)


def main():
    """Pull full 5-year dataset and save to CSV."""
    start_date = "2021-02-25T00"
    end_date = "2026-02-25T23"

    df = pull_date_range(start_date, end_date)

    outfile = "eia_solar_hourly.csv"
    df.to_csv(outfile, index=False)
    print(f"\nSaved {len(df):,} rows to {outfile}")

    print("\n--- Summary ---")
    print(f"Date range: {df['period'].min()} to {df['period'].max()}")
    print(f"\nRows per respondent:")
    print(df.groupby("respondent")["value"].agg(["count", "sum", "mean"]).to_string())


if __name__ == "__main__":
    main()
