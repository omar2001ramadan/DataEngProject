"""
Full pipeline entry point.

Step 1: Load historical CSVs into PostgreSQL (ingest.py)
Step 2: Pull fresh EIA solar data from the latest record to now
Step 3: Pull fresh sunrise/sunset data from the latest record to now
Step 4: Rebuild materialized views

Usage:
  docker compose exec backend python scripts/run_pipeline.py
"""

import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine, text

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from config import DATABASE_URL

engine = create_engine(DATABASE_URL)

# --- EIA Solar Pull ---

EIA_API_KEY = os.environ.get("EIA_API_KEY", "TOgKBkcA9l7RNC45V7BuyvdvxZTeceisVTjrHqRx")
EIA_BASE_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
RESPONDENTS = ["CISO", "ERCO"]


def get_latest_solar_period():
    """Get the most recent solar generation timestamp in the database."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT MAX(period) FROM solar_generation")).scalar()
    return result


def fetch_eia_page(offset, start_date, end_date):
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": RESPONDENTS,
        "facets[fueltype][]": "SUN",
        "start": start_date,
        "end": end_date,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": offset,
        "length": 5000,
    }
    for attempt in range(5):
        resp = requests.get(EIA_BASE_URL, params=params, timeout=60)
        if resp.status_code == 429:
            wait = 60 * (attempt + 1)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise Exception(f"EIA API failed after retries at offset {offset}")


def pull_fresh_solar(region_map):
    """Pull EIA solar data from the latest DB record to now and insert new rows."""
    latest = get_latest_solar_period()
    if latest is None:
        print("  No existing solar data, skipping fresh pull.")
        return 0

    start_str = (latest + timedelta(hours=1)).strftime("%Y-%m-%dT%H")
    end_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    print(f"  Pulling EIA solar from {start_str} to {end_str}...")

    all_records = []
    offset = 0
    while True:
        data = fetch_eia_page(offset, start_str, end_str)
        total = int(data["response"]["total"])
        records = data["response"]["data"]
        if not records:
            break
        all_records.extend(records)
        offset += 5000
        print(f"  Fetched {len(all_records):,} / {total:,}")
        if offset >= total:
            break
        time.sleep(2)

    if not all_records:
        print("  No new solar records available.")
        return 0

    df = pd.DataFrame(all_records)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df = df[df["fueltype"] == "SUN"].copy()
    df = df.dropna(subset=["period", "respondent", "value"])
    df = df[df["respondent"].isin(RESPONDENTS)].copy()
    df = df.drop_duplicates(subset=["respondent", "period"])
    df.loc[df["value"] < 0, "value"] = 0

    df["region_id"] = df["respondent"].map(region_map)
    df["value_mwh"] = df["value"]
    df = df[["period", "region_id", "value_mwh"]].dropna()
    df["region_id"] = df["region_id"].astype(int)

    df.to_sql("solar_generation", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"  Inserted {len(df)} new solar rows.")
    return len(df)


# --- Sunrise/Sunset Pull ---

def get_latest_sunrise_date(region_id):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT MAX(date) FROM sunrise_sunset WHERE region_id = :rid"),
            {"rid": region_id}
        ).scalar()
    return result


def fetch_sunrise_sunset(lat, lng, dt):
    url = "https://api.sunrise-sunset.org/json"
    params = {"lat": lat, "lng": lng, "date": dt.isoformat(), "formatted": 0}
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "OK":
                return data["results"]
        except Exception as e:
            time.sleep(5 * (attempt + 1))
    return None


SITE_COORDS = {
    "CISO": {"lat": 35.0, "lng": -118.0},
    "ERCO": {"lat": 31.8, "lng": -99.4},
}


def pull_fresh_sunrise(region_map):
    """Pull sunrise/sunset data from the latest DB record to today."""
    total_inserted = 0
    today = date.today()

    for region_code, coords in SITE_COORDS.items():
        region_id = region_map[region_code]
        latest = get_latest_sunrise_date(region_id)
        if latest is None:
            print(f"  No existing sunrise data for {region_code}, skipping.")
            continue

        start = latest + timedelta(days=1)
        if start > today:
            print(f"  {region_code} sunrise data is current.")
            continue

        days_needed = (today - start).days + 1
        print(f"  Pulling {days_needed} days of sunrise/sunset for {region_code}...")

        rows = []
        current = start
        while current <= today:
            result = fetch_sunrise_sunset(coords["lat"], coords["lng"], current)
            if result:
                sunrise = pd.to_datetime(result.get("sunrise"), errors="coerce")
                sunset = pd.to_datetime(result.get("sunset"), errors="coerce")
                day_length = result.get("day_length")
                if sunrise is not pd.NaT and sunset is not pd.NaT and sunrise < sunset:
                    rows.append({
                        "region_id": region_id,
                        "date": current,
                        "sunrise": sunrise,
                        "sunset": sunset,
                        "day_length_seconds": int(day_length),
                    })
            current += timedelta(days=1)
            time.sleep(0.5)

        if rows:
            df = pd.DataFrame(rows)
            df.to_sql("sunrise_sunset", engine, if_exists="append", index=False, method="multi")
            print(f"  Inserted {len(df)} new sunrise/sunset rows for {region_code}.")
            total_inserted += len(df)

    return total_inserted


# --- Materialized View Refresh ---

def refresh_views():
    print("Refreshing materialized views...")
    with engine.connect() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW daily_summary"))
        conn.execute(text("REFRESH MATERIALIZED VIEW monthly_summary"))
        conn.commit()
    print("  Views refreshed.")


# --- Main ---

def main():
    print("=" * 50)
    print("Solar Energy Pipeline")
    print("=" * 50)

    # Step 1: Run historical ingestion
    print("\n[Step 1] Loading historical data from CSVs...")
    from scripts.ingest import main as ingest_main
    ingest_main()

    # Get region map for fresh pulls
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, code FROM regions")).fetchall()
        region_map = {row[1]: row[0] for row in rows}

    # Step 2: Pull fresh solar data
    print("\n[Step 2] Pulling fresh EIA solar data...")
    new_solar = pull_fresh_solar(region_map)

    # Step 3: Pull fresh sunrise/sunset data
    print("\n[Step 3] Pulling fresh sunrise/sunset data...")
    new_sunrise = pull_fresh_sunrise(region_map)

    # Step 4: Refresh views if new data was added
    if new_solar > 0 or new_sunrise > 0:
        print("\n[Step 4] Refreshing materialized views...")
        refresh_views()
    else:
        print("\n[Step 4] No new data, views already current.")

    # Summary
    print("\n" + "=" * 50)
    print("Pipeline complete!")
    with engine.connect() as conn:
        for table in ["regions", "weather_stations", "solar_generation",
                       "weather_hourly", "sunrise_sunset", "daily_summary", "monthly_summary"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count:,} rows")
    print("=" * 50)


if __name__ == "__main__":
    main()
