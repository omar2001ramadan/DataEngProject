"""
Pull 5 years of hourly solar generation data from the EIA API v2
for CISO (California ISO) and ERCO (Texas ERCOT).

Data source: https://api.eia.gov/v2/electricity/rto/fuel-type-data/
Fuel type: SUN (Solar)
"""

import requests
import pandas as pd
import time
from datetime import datetime

API_KEY = "TOgKBkcA9l7RNC45V7BuyvdvxZTeceisVTjrHqRx"
BASE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"

RESPONDENTS = ["CISO", "ERCO"]
FUEL_TYPE = "SUN"
START_DATE = "2021-02-25T00"  # 5 years ago from today
END_DATE = "2026-02-25T23"
MAX_ROWS = 5000
REQUEST_DELAY = 2  # seconds between requests
MAX_RETRIES = 10


def fetch_page(offset):
    """Fetch a single page of results from the EIA API with retry on 429."""
    params = {
        "api_key": API_KEY,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": RESPONDENTS,
        "facets[fueltype][]": FUEL_TYPE,
        "start": START_DATE,
        "end": END_DATE,
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


def main():
    all_records = []
    offset = 0

    # First request to get total count
    print("Fetching first page to determine total records...")
    data = fetch_page(offset)
    total = int(data["response"]["total"])
    records = data["response"]["data"]
    all_records.extend(records)
    print(f"Total records available: {total:,}")
    print(f"Requests needed: {(total // MAX_ROWS) + 1}")
    print(f"Fetched {len(all_records):,} / {total:,}")

    offset += MAX_ROWS

    while offset < total:
        time.sleep(REQUEST_DELAY)
        data = fetch_page(offset)
        records = data["response"]["data"]
        if not records:
            break
        all_records.extend(records)
        offset += MAX_ROWS
        print(f"Fetched {len(all_records):,} / {total:,}")

    # Build DataFrame
    df = pd.DataFrame(all_records)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["period"] = pd.to_datetime(df["period"])
    df.sort_values(["respondent", "period"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Save to CSV
    outfile = "eia_solar_hourly.csv"
    df.to_csv(outfile, index=False)
    print(f"\nSaved {len(df):,} rows to {outfile}")

    # Summary
    print("\n--- Summary ---")
    print(f"Date range: {df['period'].min()} to {df['period'].max()}")
    print(f"\nRows per respondent:")
    print(df.groupby(["respondent", "respondent-name"])["value"].agg(["count", "sum", "mean"]).to_string())


if __name__ == "__main__":
    main()
