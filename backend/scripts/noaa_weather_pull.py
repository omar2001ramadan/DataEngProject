"""
Pull 5 years of hourly weather data from the NCEI Local Climatological Data API
for stations near CISO (California ISO) and ERCO (Texas ERCOT) solar regions.

Data source: https://www.ncei.noaa.gov/access/services/data/v1
Dataset: local-climatological-data
"""

import requests
import pandas as pd

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

START_DATE = "2021-02-25"
END_DATE = "2026-02-25"

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


def pull_site(name, station, desc):
    print(f"\nPulling {name}: {desc} (station {station})...")
    params = {
        "dataset": "local-climatological-data",
        "stations": station,
        "startDate": START_DATE,
        "endDate": END_DATE,
        "dataTypes": ",".join(HOURLY_FIELDS),
        "format": "csv",
        "includeStationName": "true",
        "includeStationLocation": "1",
        "units": "metric",
    }
    resp = requests.get(BASE_URL, params=params, timeout=120)
    resp.raise_for_status()

    # Write raw response then read back with pandas
    raw_file = f"weather_{name}_raw.csv"
    with open(raw_file, "wb") as f:
        f.write(resp.content)

    df = pd.read_csv(raw_file, low_memory=False)
    print(f"  Raw rows: {len(df):,}")

    # Keep only columns we care about
    keep_cols = ["STATION", "NAME", "LATITUDE", "LONGITUDE", "DATE"] + HOURLY_FIELDS
    keep_cols = [c for c in keep_cols if c in df.columns]
    df = df[keep_cols]

    # Drop rows where all hourly fields are empty (daily summary rows)
    df = df.dropna(subset=HOURLY_FIELDS, how="all")

    df["DATE"] = pd.to_datetime(df["DATE"])
    df.sort_values("DATE", inplace=True)
    df.reset_index(drop=True, inplace=True)

    outfile = f"weather_{name}.csv"
    df.to_csv(outfile, index=False)
    print(f"  Hourly rows kept: {len(df):,}")
    print(f"  Date range: {df['DATE'].min()} to {df['DATE'].max()}")
    print(f"  Saved to {outfile}")

    # Clean up raw file
    import os
    os.remove(raw_file)

    return df


def main():
    for name, info in SITES.items():
        pull_site(name, info["station"], info["desc"])
    print("\nDone!")


if __name__ == "__main__":
    main()
