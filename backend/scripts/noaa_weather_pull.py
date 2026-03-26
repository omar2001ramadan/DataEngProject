"""
Sanbir Rahman
Pull hourly weather data from the NCEI Local Climatological Data API
for stations near CISO (California ISO) and ERCO (Texas ERCOT) solar regions.

Data source: https://www.ncei.noaa.gov/access/services/data/v1
Dataset: local-climatological-data
"""

import os
import requests
import pandas as pd
from io import StringIO

BASE_URL = "https://www.ncei.noaa.gov/access/services/data/v1"

SITES = {
    "CISO": {
        "station": "72381023114",
        "desc": "Edwards AFB, CA (34.9°N, 117.9°W)",
    },
    "ERCO": {
        "station": "72266693943",
        "desc": "Brownwood Municipal Airport, TX (31.8°N, 99.0°W)",
    },
}

HOURLY_FIELDS = [
    "HourlyDryBulbTemperature",
    "HourlyDewPointTemperature",
    "HourlyRelativeHumidity",
    "HourlyWindSpeed",
    "HourlyWindDirection",
    "HourlyWindGustSpeed",
    "HourlyPrecipitation",
    "HourlySkyConditions",
    "HourlyVisibility",
    "HourlyStationPressure",
    "HourlyAltimeterSetting",
    "HourlyWetBulbTemperature",
]


def clean(df):
    """Apply cleaning: type conversion, null filtering, deduplication."""
    keep_cols = ["STATION", "NAME", "LATITUDE", "LONGITUDE", "DATE"] + HOURLY_FIELDS
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols].copy()

    # Drop rows where all hourly fields are empty
    hourly_present = [c for c in HOURLY_FIELDS if c in df.columns]
    df = df.dropna(subset=hourly_present, how="all")

    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")

    # Numeric conversions
    numeric_cols = [
        "HourlyDryBulbTemperature", "HourlyDewPointTemperature",
        "HourlyRelativeHumidity", "HourlyWindSpeed", "HourlyWindDirection",
        "HourlyWindGustSpeed", "HourlyPrecipitation", "HourlyVisibility",
        "HourlyStationPressure", "HourlyAltimeterSetting", "HourlyWetBulbTemperature",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "HourlyPrecipitation" in df.columns:
        df["HourlyPrecipitation"] = df["HourlyPrecipitation"].fillna(0)

    df = df.dropna(subset=["STATION", "DATE", "NAME", "LATITUDE", "LONGITUDE"])
    df = df.drop_duplicates(subset=["STATION", "DATE"])
    df = df.sort_values("DATE").reset_index(drop=True)
    return df


def pull_date_range(respondent_id, start_date, end_date):
    """Pull and clean weather data for one station and date range.

    Args:
        respondent_id: Region code ("CISO" or "ERCO")
        start_date: Start date string (e.g. "2025-09-01")
        end_date: End date string (e.g. "2026-03-26")

    Returns:
        Cleaned DataFrame with NOAA weather observations
    """
    if respondent_id not in SITES:
        raise ValueError(f"Unknown respondent: {respondent_id}")

    site = SITES[respondent_id]
    print(f"  Pulling weather for {respondent_id}: {site['desc']}...")
    print(f"  Date range: {start_date} to {end_date}")

    params = {
        "dataset": "local-climatological-data",
        "stations": site["station"],
        "startDate": start_date,
        "endDate": end_date,
        "dataTypes": ",".join(HOURLY_FIELDS),
        "format": "csv",
        "includeStationName": "true",
        "includeStationLocation": "1",
        "units": "metric",
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=120)
        resp.raise_for_status()
    except Exception as e:
        print(f"  NOAA API error: {e}")
        return pd.DataFrame()

    if not resp.text.strip() or resp.text.strip().startswith("<"):
        print("  No data returned from NOAA.")
        return pd.DataFrame()

    df = pd.read_csv(StringIO(resp.text), low_memory=False)
    print(f"  Raw rows: {len(df):,}")

    if df.empty:
        return df

    df = clean(df)
    print(f"  Cleaned rows: {len(df):,}")
    return df


def main():
    """Pull full dataset and save to CSV per site."""
    start_date = "2021-02-25"
    end_date = "2026-02-25"

    for name, info in SITES.items():
        print(f"\nPulling {name}: {info['desc']}...")
        df = pull_date_range(name, start_date, end_date)

        outfile = f"weather_{name}.csv"
        df.to_csv(outfile, index=False)
        print(f"  Saved {len(df):,} rows to {outfile}")

    print("\nDone!")


if __name__ == "__main__":
    main()
