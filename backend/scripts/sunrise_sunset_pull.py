"""
Sanbir Rahman
Pull daily sunrise/sunset data for CISO and ERCO solar regions
using the Sunrise-Sunset API (https://sunrise-sunset.org/api).
"""

import requests
import csv
import time
import pandas as pd
from datetime import date, timedelta

SITES = {
    "CISO": {"lat": 35.0, "lng": -118.0, "desc": "California ISO (Mojave solar region)"},
    "ERCO": {"lat": 31.8, "lng": -99.4, "desc": "ERCOT Texas (central TX solar region)"},
}

REQUEST_DELAY = 0.5  # seconds between requests

FIELDS = [
    "date", "sunrise", "sunset", "solar_noon", "day_length",
    "civil_twilight_begin", "civil_twilight_end",
    "nautical_twilight_begin", "nautical_twilight_end",
    "astronomical_twilight_begin", "astronomical_twilight_end",
]


def fetch_day(lat, lng, dt):
    """Fetch sunrise/sunset for one date. Returns dict or None on failure."""
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
            wait = 5 * (attempt + 1)
            print(f"  Retry {attempt+1}/3 for {dt} ({e}). Waiting {wait}s...")
            time.sleep(wait)
    return None


def clean(df):
    """Apply cleaning: type conversion, null/duplicate removal, validation."""
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    time_cols = ["sunrise", "sunset", "solar_noon",
                 "civil_twilight_begin", "civil_twilight_end",
                 "nautical_twilight_begin", "nautical_twilight_end",
                 "astronomical_twilight_begin", "astronomical_twilight_end"]
    for col in time_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    df["day_length"] = pd.to_numeric(df["day_length"], errors="coerce")

    # Drop rows missing key fields
    df = df.dropna(subset=["date", "sunrise", "sunset", "day_length"])

    # Remove invalid rows where sunrise is after sunset
    df = df[df["sunrise"] < df["sunset"]]

    # Remove duplicates
    df = df.drop_duplicates(subset=["date"])

    df = df.sort_values("date").reset_index(drop=True)
    return df


def pull_date_range(respondent_id, start_dt, end_dt):
    """Pull and clean sunrise/sunset data for one region and date range.

    Args:
        respondent_id: Region code ("CISO" or "ERCO")
        start_dt: Start date (datetime.date)
        end_dt: End date (datetime.date)

    Returns:
        Cleaned DataFrame with sunrise/sunset fields
    """
    if respondent_id not in SITES:
        raise ValueError(f"Unknown respondent: {respondent_id}")

    coords = SITES[respondent_id]
    days_needed = (end_dt - start_dt).days + 1
    print(f"  Pulling {days_needed} days of sunrise/sunset for {respondent_id}...")

    records = []
    current = start_dt
    while current <= end_dt:
        result = fetch_day(coords["lat"], coords["lng"], current)
        if result:
            row = {"date": current.isoformat()}
            for key in FIELDS[1:]:
                row[key] = result.get(key, "")
            records.append(row)
        current += timedelta(days=1)
        time.sleep(REQUEST_DELAY)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    return clean(df)


def main():
    """Pull full dataset and save to CSV per site."""
    start_dt = date(2021, 2, 25)
    end_dt = date(2026, 2, 25)

    for name, info in SITES.items():
        print(f"\nPulling sunrise/sunset for {name} ({info['desc']})...")
        print(f"  Coordinates: {info['lat']}, {info['lng']}")
        df = pull_date_range(name, start_dt, end_dt)

        outfile = f"sunrise_sunset_{name}.csv"
        df.to_csv(outfile, index=False)
        print(f"  Saved {len(df)} rows to {outfile}")

    print("\nComplete!")


if __name__ == "__main__":
    main()
