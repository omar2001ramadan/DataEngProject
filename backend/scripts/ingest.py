"""
CSV -> PostgreSQL ingestion script (3NF schema).
Usage:
  cd backend && python scripts/ingest.py
  OR: cd project_root && python -m backend.scripts.ingest
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Ensure backend/ is on the path so we can import config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from config import DATABASE_URL

# Check backend/data/ first (Railway), then project root data/
DATA_DIR = os.path.join(BACKEND_DIR, "data")
if not os.path.isdir(DATA_DIR):
    DATA_DIR = os.path.join(PROJECT_DIR, "data")

engine = create_engine(DATABASE_URL)

# Region metadata
REGIONS = {
    "CISO": "California Independent System Operator",
    "ERCO": "Electric Reliability Council of Texas",
}

# Station metadata extracted from CSVs
STATIONS = {
    "CISO": {
        "station_code": "72381023114",
        "name": "EDWARDS AFB, CA US",
        "latitude": 34.9,
        "longitude": -117.86667,
    },
    "ERCO": {
        "station_code": "72266693943",
        "name": "BROWNWOOD MUNICIPAL AIRPORT, TX US",
        "latitude": 31.8,
        "longitude": -98.95,
    },
}


def load_regions():
    """Create and populate the regions table. Returns {code: id} mapping."""
    print("Loading regions...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS solar_generation, weather_hourly, sunrise_sunset, weather_stations, regions CASCADE"))
        conn.execute(text("""
            CREATE TABLE regions (
                id SERIAL PRIMARY KEY,
                code VARCHAR(10) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL
            )
        """))
        for code, name in REGIONS.items():
            conn.execute(text("INSERT INTO regions (code, name) VALUES (:code, :name)"), {"code": code, "name": name})
        conn.commit()

        rows = conn.execute(text("SELECT id, code FROM regions")).fetchall()
        region_map = {row[1]: row[0] for row in rows}
    print(f"  Loaded {len(region_map)} regions: {region_map}")
    return region_map


def load_weather_stations(region_map):
    """Create and populate weather_stations table. Returns {region_code: station_id} mapping."""
    print("Loading weather stations...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE weather_stations (
                id SERIAL PRIMARY KEY,
                region_id INTEGER NOT NULL REFERENCES regions(id),
                station_code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL
            )
        """))
        for region_code, info in STATIONS.items():
            conn.execute(text("""
                INSERT INTO weather_stations (region_id, station_code, name, latitude, longitude)
                VALUES (:region_id, :station_code, :name, :latitude, :longitude)
            """), {"region_id": region_map[region_code], **info})
        conn.commit()

        rows = conn.execute(text("""
            SELECT ws.id, r.code FROM weather_stations ws
            JOIN regions r ON ws.region_id = r.id
        """)).fetchall()
        station_map = {row[1]: row[0] for row in rows}
    print(f"  Loaded {len(station_map)} stations: {station_map}")
    return station_map


def load_solar(region_map):
    print("Loading solar generation data...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE solar_generation (
                id SERIAL PRIMARY KEY,
                period TIMESTAMP NOT NULL,
                region_id INTEGER NOT NULL REFERENCES regions(id),
                value_mwh FLOAT NOT NULL
            )
        """))
        conn.commit()

    df = pd.read_csv(os.path.join(DATA_DIR, "eia_solar_hourly.csv"))
    df["period"] = pd.to_datetime(df["period"])
    df["value_mwh"] = pd.to_numeric(df["value"], errors="coerce")
    df["region_id"] = df["respondent"].map(region_map)
    df = df[["period", "region_id", "value_mwh"]].dropna(subset=["value_mwh", "region_id"])
    df["region_id"] = df["region_id"].astype(int)
    df.to_sql("solar_generation", engine, if_exists="append", index=False, method="multi", chunksize=5000)

    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX idx_solar_period ON solar_generation(period)"))
        conn.execute(text("CREATE INDEX idx_solar_region_id ON solar_generation(region_id)"))
        conn.commit()
    print(f"  Loaded {len(df)} solar rows")


def load_weather(station_map):
    print("Loading weather data...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE weather_hourly (
                id SERIAL PRIMARY KEY,
                station_id INTEGER NOT NULL REFERENCES weather_stations(id),
                hour TIMESTAMP NOT NULL,
                temperature FLOAT,
                dew_point FLOAT,
                humidity FLOAT,
                wind_speed FLOAT,
                wind_direction VARCHAR(10),
                wind_gust FLOAT,
                precipitation FLOAT,
                visibility FLOAT,
                pressure FLOAT
            )
        """))
        conn.commit()

    total = 0
    for region_code, filename in [("CISO", "weather_CISO.csv"), ("ERCO", "weather_ERCO.csv")]:
        df = pd.read_csv(os.path.join(DATA_DIR, filename))
        df["station_id"] = station_map[region_code]
        df["hour"] = pd.to_datetime(df["DATE"]).dt.floor("h")
        df["temperature"] = pd.to_numeric(df["HourlyDryBulbTemperature"], errors="coerce")
        df["dew_point"] = pd.to_numeric(df["HourlyDewPointTemperature"], errors="coerce")
        df["humidity"] = pd.to_numeric(df["HourlyRelativeHumidity"], errors="coerce")
        df["wind_speed"] = pd.to_numeric(df["HourlyWindSpeed"], errors="coerce")
        df["wind_direction"] = df["HourlyWindDirection"].astype(str)
        df["wind_gust"] = pd.to_numeric(df["HourlyWindGustSpeed"], errors="coerce")
        df["precipitation"] = pd.to_numeric(df["HourlyPrecipitation"], errors="coerce")
        df["visibility"] = pd.to_numeric(df["HourlyVisibility"], errors="coerce")
        df["pressure"] = pd.to_numeric(df["HourlyStationPressure"], errors="coerce")

        agg_cols = {
            "temperature": "mean", "dew_point": "mean", "humidity": "mean",
            "wind_speed": "mean", "wind_gust": "mean", "precipitation": "sum",
            "visibility": "mean", "pressure": "mean",
        }
        hourly = df.groupby(["station_id", "hour"]).agg(agg_cols).reset_index()
        wind_dir = df.groupby(["station_id", "hour"])["wind_direction"].first().reset_index()
        hourly = hourly.merge(wind_dir, on=["station_id", "hour"])

        hourly.to_sql("weather_hourly", engine, if_exists="append", index=False, method="multi", chunksize=5000)
        print(f"  {region_code}: {len(hourly)} hourly rows")
        total += len(hourly)

    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX idx_weather_hour ON weather_hourly(hour)"))
        conn.execute(text("CREATE INDEX idx_weather_station_id ON weather_hourly(station_id)"))
        conn.commit()
    print(f"  Total weather rows: {total}")


def load_sunrise_sunset(region_map):
    print("Loading sunrise/sunset data...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE sunrise_sunset (
                id SERIAL PRIMARY KEY,
                region_id INTEGER NOT NULL REFERENCES regions(id),
                date DATE NOT NULL,
                sunrise TIMESTAMP NOT NULL,
                sunset TIMESTAMP NOT NULL,
                day_length_seconds INTEGER NOT NULL
            )
        """))
        conn.commit()

    total = 0
    for region_code, filename in [("CISO", "sunrise_sunset_CISO.csv"), ("ERCO", "sunrise_sunset_ERCO.csv")]:
        df = pd.read_csv(os.path.join(DATA_DIR, filename))
        df["region_id"] = region_map[region_code]
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["sunrise"] = pd.to_datetime(df["sunrise"])
        df["sunset"] = pd.to_datetime(df["sunset"])
        df["day_length_seconds"] = pd.to_numeric(df["day_length"], errors="coerce")
        result = df[["region_id", "date", "sunrise", "sunset", "day_length_seconds"]].dropna()
        result.to_sql("sunrise_sunset", engine, if_exists="append", index=False, method="multi", chunksize=5000)
        print(f"  {region_code}: {len(result)} rows")
        total += len(result)

    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX idx_sun_date ON sunrise_sunset(date)"))
        conn.execute(text("CREATE INDEX idx_sun_region_id ON sunrise_sunset(region_id)"))
        conn.commit()
    print(f"  Total sunrise/sunset rows: {total}")


def create_materialized_views():
    print("Creating materialized views...")
    with engine.connect() as conn:
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS monthly_summary CASCADE"))
        conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS daily_summary CASCADE"))

        conn.execute(text("""
            CREATE MATERIALIZED VIEW daily_summary AS
            SELECT
                r.code AS region,
                DATE(s.period) AS date,
                SUM(s.value_mwh) AS total_mwh,
                MAX(s.value_mwh) AS peak_mwh,
                COUNT(s.*) AS solar_hours,
                AVG(w.temperature) AS avg_temperature,
                AVG(w.humidity) AS avg_humidity,
                AVG(w.wind_speed) AS avg_wind_speed,
                AVG(w.visibility) AS avg_visibility,
                AVG(w.pressure) AS avg_pressure,
                MIN(ss.day_length_seconds) AS day_length_seconds,
                MIN(ss.sunrise) AS sunrise,
                MIN(ss.sunset) AS sunset
            FROM solar_generation s
            JOIN regions r ON s.region_id = r.id
            LEFT JOIN weather_stations ws ON ws.region_id = r.id
            LEFT JOIN weather_hourly w
                ON w.station_id = ws.id
                AND DATE(s.period) = DATE(w.hour)
                AND EXTRACT(HOUR FROM s.period) = EXTRACT(HOUR FROM w.hour)
            LEFT JOIN sunrise_sunset ss
                ON ss.region_id = r.id
                AND DATE(s.period) = ss.date
            GROUP BY r.code, DATE(s.period)
            ORDER BY r.code, DATE(s.period)
        """))
        conn.execute(text("CREATE INDEX ON daily_summary(region, date)"))

        conn.execute(text("""
            CREATE MATERIALIZED VIEW monthly_summary AS
            SELECT
                region,
                DATE_TRUNC('month', date)::date AS month,
                SUM(total_mwh) AS total_mwh,
                AVG(total_mwh) AS avg_daily_mwh,
                MAX(peak_mwh) AS peak_mwh,
                AVG(avg_temperature) AS avg_temperature,
                AVG(avg_humidity) AS avg_humidity,
                AVG(avg_wind_speed) AS avg_wind_speed,
                AVG(day_length_seconds) AS avg_day_length_seconds,
                COUNT(*) AS days_in_month
            FROM daily_summary
            GROUP BY region, DATE_TRUNC('month', date)
            ORDER BY region, month
        """))
        conn.execute(text("CREATE INDEX ON monthly_summary(region, month)"))
        conn.commit()
    print("  Materialized views created.")


def main():
    print(f"Connecting to: {DATABASE_URL[:30]}...")
    region_map = load_regions()
    station_map = load_weather_stations(region_map)
    load_solar(region_map)
    load_weather(station_map)
    load_sunrise_sunset(region_map)
    create_materialized_views()
    print("\nIngestion complete!")

    with engine.connect() as conn:
        for table in ["regions", "weather_stations", "solar_generation", "weather_hourly", "sunrise_sunset", "daily_summary", "monthly_summary"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()
