"""
Pull daily sunrise/sunset data for CISO and ERCO solar regions
using the Sunrise-Sunset API (https://sunrise-sunset.org/api).

Produces one CSV per site.
"""

import requests
import csv
import time
from datetime import date, timedelta

SITES = {
    "CISO": {"lat": 35.0, "lng": -118.0, "desc": "California ISO (Mojave solar region)"},
    "ERCO": {"lat": 31.8, "lng": -99.4, "desc": "ERCOT Texas (central TX solar region)"},
}

START_DATE = date(2021, 2, 25)
END_DATE = date(2026, 2, 25)
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


def pull_site(name, lat, lng):
    total_days = (END_DATE - START_DATE).days + 1
    outfile = f"sunrise_sunset_{name}.csv"

    with open(outfile, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        current = START_DATE
        day_num = 0
        while current <= END_DATE:
            result = fetch_day(lat, lng, current)
            if result:
                row = {"date": current.isoformat()}
                for key in FIELDS[1:]:
                    row[key] = result.get(key, "")
                writer.writerow(row)
            else:
                print(f"  WARNING: No data for {current}")

            day_num += 1
            if day_num % 100 == 0:
                print(f"  {name}: {day_num:,} / {total_days:,} days fetched")

            current += timedelta(days=1)
            time.sleep(REQUEST_DELAY)

    print(f"  {name}: Done — saved {day_num:,} days to {outfile}")


def main():
    for name, info in SITES.items():
        print(f"\nPulling sunrise/sunset for {name} ({info['desc']})...")
        print(f"  Coordinates: {info['lat']}, {info['lng']}")
        pull_site(name, info["lat"], info["lng"])

    print("\nComplete!")


if __name__ == "__main__":
    main()
