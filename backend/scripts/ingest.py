"""
CSV -> PostgreSQL ingestion script (3NF schema matching ERD).
Orchestrates the build_tables scripts to create and populate tables,
then creates materialized views for the API.

Usage:
  cd backend && python scripts/ingest.py
"""
import os
import sys
import psycopg2
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
        cur.execute("DROP TABLE IF EXISTS Solar_Generation CASCADE")
        cur.execute("DROP TABLE IF EXISTS Weather_Observation CASCADE")
        cur.execute("DROP TABLE IF EXISTS Daily_Solar_Timing CASCADE")
        cur.execute("DROP TABLE IF EXISTS Weather_Station CASCADE")
        cur.execute("DROP TABLE IF EXISTS Respondent CASCADE")
        cur.execute("DROP TABLE IF EXISTS Date_Dimension CASCADE")
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
            FROM Solar_Generation s
            JOIN Respondent r ON s.respondent_id = r.respondent_id
            LEFT JOIN Weather_Station ws ON ws.respondent_id = r.respondent_id
            LEFT JOIN Weather_Observation w
                ON w.station_id = ws.station_id
                AND DATE(s.period) = DATE(w.observation_datetime)
                AND EXTRACT(HOUR FROM s.period) = EXTRACT(HOUR FROM w.observation_datetime)
            LEFT JOIN Daily_Solar_Timing t
                ON t.respondent_id = r.respondent_id
                AND DATE(s.period) = t.date
            GROUP BY r.respondent_id, DATE(s.period)
            ORDER BY r.respondent_id, DATE(s.period)
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

    # Build views
    print("\n--- Building views ---")

    from build_merged_view import create_view
    create_view()

    create_materialized_views()

    # Summary
    print("\nIngestion complete!")
    with engine.connect() as conn:
        for table in ['Date_Dimension', 'Respondent', 'Weather_Station',
                       'Solar_Generation', 'Weather_Observation', 'Daily_Solar_Timing',
                       'daily_summary', 'monthly_summary']:
            count = conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
            print(f"  {table}: {count:,} rows")


if __name__ == "__main__":
    main()
