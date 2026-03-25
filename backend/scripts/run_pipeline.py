"""
Burch Parshall
Full pipeline entry point.

Step 1: Load historical CSVs into PostgreSQL via team build_tables scripts
Step 2: Pull fresh EIA solar data from the latest record to now (Sanbir's pull script)
Step 3: Pull fresh sunrise/sunset data from the latest record to now (Sanbir's pull script)
Step 4: Rebuild materialized views

Usage:
  docker compose exec backend python scripts/run_pipeline.py
"""

import os
import sys
import pandas as pd
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import create_engine, text

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SCRIPT_DIR)

from config import DATABASE_URL
from eia_solar_pull import pull_date_range as pull_eia_solar
from sunrise_sunset_pull import pull_date_range as pull_sunrise_sunset

engine = create_engine(DATABASE_URL)

RESPONDENTS = ["CISO", "ERCO"]


def get_latest_solar_period():
    with engine.connect() as conn:
        return conn.execute(text("SELECT MAX(period) FROM solar_generation")).scalar()


def get_latest_timing_date(respondent_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT MAX(date) FROM daily_solar_timing WHERE respondent_id = :rid"),
            {"rid": respondent_id}
        ).scalar()


def pull_fresh_solar():
    """Use Sanbir's EIA pull to get data from the latest DB record to now."""
    latest = get_latest_solar_period()
    if latest is None:
        print("  No existing solar data, skipping fresh pull.")
        return 0

    start_str = (latest + timedelta(hours=1)).strftime("%Y-%m-%dT%H")
    end_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

    df = pull_eia_solar(start_str, end_str)
    if df.empty:
        print("  No new solar records available.")
        return 0

    # Map to DB columns
    df["respondent_id"] = df["respondent"]
    df["date_id"] = df["period"].dt.date
    df["value_mwh"] = df["value"]
    df = df[["respondent_id", "period", "date_id", "value_mwh"]].dropna()

    df.to_sql("solar_generation", engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"  Inserted {len(df)} new solar rows.")
    return len(df)


def pull_fresh_timing():
    """Use Sanbir's sunrise/sunset pull to get data from the latest DB record to today."""
    total_inserted = 0
    today = date.today()

    for respondent_id in RESPONDENTS:
        latest = get_latest_timing_date(respondent_id)
        if latest is None:
            print(f"  No existing timing data for {respondent_id}, skipping.")
            continue

        start_dt = latest + timedelta(days=1)
        if start_dt > today:
            print(f"  {respondent_id} timing data is current.")
            continue

        df = pull_sunrise_sunset(respondent_id, start_dt, today)
        if df.empty:
            continue

        # Map to DB columns
        df["respondent_id"] = respondent_id
        df["date_id"] = pd.to_datetime(df["date"]).dt.date
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["day_length_sec"] = df["day_length"]

        # Rename astronomical columns to match schema
        rename = {
            "astronomical_twilight_begin": "astronomical_twilight_begin",
            "astronomical_twilight_end": "astronomical_twilight_end",
        }
        df = df.rename(columns=rename)

        out_cols = [
            "respondent_id", "date_id", "date", "sunrise", "sunset", "solar_noon",
            "day_length_sec", "civil_twilight_begin", "civil_twilight_end",
            "nautical_twilight_begin", "nautical_twilight_end",
            "astronomical_twilight_begin", "astronomical_twilight_end",
        ]
        for col in out_cols:
            if col not in df.columns:
                df[col] = None
        df = df[out_cols]

        df.to_sql("daily_solar_timing", engine, if_exists="append", index=False, method="multi")
        print(f"  Inserted {len(df)} new timing rows for {respondent_id}.")
        total_inserted += len(df)

    return total_inserted


def refresh_views():
    print("Refreshing materialized views...")
    with engine.connect() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW daily_summary"))
        conn.execute(text("REFRESH MATERIALIZED VIEW monthly_summary"))
        conn.commit()
    print("  Views refreshed.")


def main():
    print("=" * 50)
    print("Solar Energy Pipeline")
    print("=" * 50)

    # Step 1: Run historical ingestion via team scripts
    print("\n[Step 1] Loading historical data from CSVs...")
    from ingest import main as ingest_main
    ingest_main()

    # Step 2: Pull fresh solar data
    print("\n[Step 2] Pulling fresh EIA solar data...")
    new_solar = pull_fresh_solar()

    # Step 3: Pull fresh sunrise/sunset data
    print("\n[Step 3] Pulling fresh sunrise/sunset data...")
    new_timing = pull_fresh_timing()

    # Step 4: Refresh views if new data was added
    if new_solar > 0 or new_timing > 0:
        print("\n[Step 4] Refreshing materialized views...")
        refresh_views()
    else:
        print("\n[Step 4] No new data, views already current.")

    # Summary
    print("\n" + "=" * 50)
    print("Pipeline complete!")
    with engine.connect() as conn:
        for table in ['date_dimension', 'respondent', 'weather_station',
                       'solar_generation', 'weather_observation', 'daily_solar_timing',
                       'daily_summary', 'monthly_summary']:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count:,} rows")
    print("=" * 50)


if __name__ == "__main__":
    main()
