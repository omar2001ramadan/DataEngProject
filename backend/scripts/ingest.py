"""
Burch Parshall
CSV -> PostgreSQL ingestion script (3NF schema matching ERD).
Orchestrates the build_tables scripts to create and populate tables,
then creates materialized views for the API.

Usage:
  cd backend && python scripts/ingest.py
"""
import os
import sys
import psycopg2
from datetime import datetime
from sqlalchemy import create_engine, text

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, SCRIPT_DIR)

from config import DATABASE_URL
from db_connect import get_connection

engine = create_engine(DATABASE_URL)


def drop_all_tables():
    """Drop all tables in dependency order for a clean rebuild."""
    print("Dropping existing tables...")
    conn = get_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP MATERIALIZED VIEW IF EXISTS monthly_summary CASCADE")
        cur.execute("DROP MATERIALIZED VIEW IF EXISTS daily_summary CASCADE")
        cur.execute("DROP VIEW IF EXISTS merged_weather_solar_view CASCADE")
        cur.execute("DROP TABLE IF EXISTS solar_capacity CASCADE")
        cur.execute("DROP TABLE IF EXISTS solar_generation CASCADE")
        cur.execute("DROP TABLE IF EXISTS weather_observation CASCADE")
        cur.execute("DROP TABLE IF EXISTS daily_solar_timing CASCADE")
        cur.execute("DROP TABLE IF EXISTS weather_station CASCADE")
        cur.execute("DROP TABLE IF EXISTS respondent CASCADE")
        cur.execute("DROP TABLE IF EXISTS date_dimension CASCADE")
    conn.close()
    print("  All tables dropped.")


def create_materialized_views():
    """Create materialized views used by the API routes."""
    print("Creating materialized views...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE MATERIALIZED VIEW daily_summary AS
            SELECT
                r.respondent_id AS region,
                DATE(s.period) AS date,
                SUM(s.value_mwh) AS total_mwh,
                MAX(s.value_mwh) AS peak_mwh,
                COUNT(s.*) AS solar_hours,
                AVG(w.dry_bulb_temp_c) AS avg_temperature,
                AVG(w.relative_humidity_pct) AS avg_humidity,
                AVG(w.wind_speed_kmh) AS avg_wind_speed,
                AVG(w.visibility_km) AS avg_visibility,
                AVG(w.station_pressure_hpa) AS avg_pressure,
                MIN(t.day_length_sec) AS day_length_seconds,
                MIN(t.sunrise) AS sunrise,
                MIN(t.sunset) AS sunset
            FROM solar_generation s
            JOIN respondent r ON s.respondent_id = r.respondent_id
            LEFT JOIN weather_station ws ON ws.respondent_id = r.respondent_id
            LEFT JOIN weather_observation w
                ON w.station_id = ws.station_id
                AND DATE(s.period) = DATE(w.observation_datetime)
                AND EXTRACT(HOUR FROM s.period) = EXTRACT(HOUR FROM w.observation_datetime)
            LEFT JOIN daily_solar_timing t
                ON t.respondent_id = r.respondent_id
                AND DATE(s.period) = t.date
            GROUP BY r.respondent_id, DATE(s.period)
            ORDER BY r.respondent_id, DATE(s.period)
        """))
        conn.execute(text("CREATE INDEX ON daily_summary(region, date)"))

        conn.execute(text("""
            CREATE MATERIALIZED VIEW monthly_summary AS
            SELECT
                ds.region,
                DATE_TRUNC('month', ds.date)::date AS month,
                SUM(ds.total_mwh) AS total_mwh,
                AVG(ds.total_mwh) AS avg_daily_mwh,
                MAX(ds.peak_mwh) AS peak_mwh,
                AVG(ds.avg_temperature) AS avg_temperature,
                AVG(ds.avg_humidity) AS avg_humidity,
                AVG(ds.avg_wind_speed) AS avg_wind_speed,
                AVG(ds.day_length_seconds) AS avg_day_length_seconds,
                COUNT(*) AS days_in_month,
                MAX(sc.capacity_mw) AS capacity_mw,
                CASE
                    WHEN MAX(sc.capacity_mw) > 0
                    THEN SUM(ds.total_mwh) / (MAX(sc.capacity_mw) * COUNT(*) * 24) * 100
                    ELSE NULL
                END AS capacity_factor_pct
            FROM daily_summary ds
            LEFT JOIN solar_capacity sc
                ON sc.respondent_id = ds.region
                AND sc.date_id = DATE_TRUNC('month', ds.date)::date
            GROUP BY ds.region, DATE_TRUNC('month', ds.date)
            ORDER BY ds.region, month
        """))
        conn.execute(text("CREATE INDEX ON monthly_summary(region, month)"))
        conn.commit()
    print("  Materialized views created.")


def main():
    print(f"Connecting to: {DATABASE_URL[:30]}...")

    # Clean slate
    drop_all_tables()

    # Build tables using team scripts (dependency order)
    print("\n--- Building tables ---")

    from build_tables_dates import main as build_dates
    build_dates()

    from build_tables_respondent import main as build_respondent
    build_respondent()

    from build_tables_station import main as build_station
    build_station()

    from build_tables_solar import main as build_solar
    build_solar()

    from build_tables_observation import main as build_observation
    build_observation()

    from build_tables_timing import main as build_timing
    build_timing()

    # Pull capacity CSV if it doesn't exist yet (initial run)
    from db_connect import data_file
    capacity_csv = data_file("eia_capacity_monthly.csv")
    if not os.path.exists(capacity_csv):
        print("\n  Capacity CSV not found, pulling from EIA API...")
        from eia_capacity_pull import pull_date_range as pull_capacity
        df = pull_capacity("2021-01", datetime.now().strftime("%Y-%m"))
        if not df.empty:
            df.to_csv(capacity_csv, index=False)
            print(f"  Saved {len(df)} rows to {capacity_csv}")

    from build_tables_capacity import main as build_capacity
    build_capacity()

    # Build views
    print("\n--- Building views ---")

    from build_merged_view import create_view
    create_view()

    create_materialized_views()

    # Summary
    print("\nIngestion complete!")
    with engine.connect() as conn:
        for table in ['date_dimension', 'respondent', 'weather_station',
                       'solar_generation', 'weather_observation', 'daily_solar_timing',
                       'solar_capacity', 'daily_summary', 'monthly_summary']:
            count = conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
            print(f"  {table}: {count:,} rows")


if __name__ == "__main__":
    main()
