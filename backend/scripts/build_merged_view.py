import psycopg2
import os
DB_HOST = "localhost"
DB_NAME = "renewable_db"
DB_USER = os.getenv('USERNAME')
DB_PASSWORD = os.getenv('PASSWORD')
DB_PORT = 5432
VIEW_NAME = "merged_weather_solar_view"
create_view_sql = f"""
    CREATE OR REPLACE VIEW {VIEW_NAME} AS
    SELECT
        -- Observation
        wo.observation_id,
        wo.observation_datetime,
        wo.dry_bulb_temp_c,
        wo.dew_point_temp_c,
        wo.relative_humidity_pct,
        wo.wet_bulb_temp_c,
        wo.wind_speed_kmh,
        wo.wind_direction_deg,
        wo.wind_gust_speed_kmh,
        wo.precipitation_mm,
        wo.sky_conditions,
        wo.visibility_km,
        wo.station_pressure_hpa,
        wo.altimeter_setting_hpa,
        -- Station
        ws.station_id,
        ws.station_name,
        ws.latitude AS station_latitude,
        ws.longitude AS station_longitude,
        -- Respondent
        r.respondent_id,
        r.respondent_name,
        r.region_latitude,
        r.region_longitude,
        -- Date Dimension
        dd.date_id,
        dd.day_of_week,
        dd.month,
        dd.month_name,
        dd.quarter,
        dd.year,
        dd.season,
        dd.is_weekend,
        -- Solar Timing
        dst.sunrise,
        dst.sunset,
        dst.solar_noon,
        dst.day_length_sec,
        dst.civil_twilight_begin,
        dst.civil_twilight_end,
        dst.nautical_twilight_begin,
        dst.nautical_twilight_end,
        dst.astronomical_twilight_begin,
        dst.astronomical_twilight_end,
        -- Solar Generation
        sg.period,
        sg.value_mwh
    FROM Weather_Observation wo
    INNER JOIN Weather_Station ws ON wo.station_id = ws.station_id
    INNER JOIN Respondent r ON ws.respondent_id = r.respondent_id
    INNER JOIN Date_Dimension dd ON wo.date_id = dd.date_id
    -- use a left join to include all weather observations even if solar timing or generation data is missing for that date/respondent
    LEFT JOIN Daily_Solar_Timing dst
        ON r.respondent_id = dst.respondent_id
        AND dd.date_id = dst.date_id
    LEFT JOIN Solar_Generation sg
        ON r.respondent_id = sg.respondent_id
        AND dd.date_id = sg.date_id;
"""

def create_view():
    # create the sql view that merges the tables from burch's schema
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    try:
        with conn.cursor() as cur:
            cur.execute(create_view_sql)
            conn.commit()
            print(f"View '{VIEW_NAME}' created successfully.")
    finally:
        conn.close()
if __name__ == "__main__":
    create_view()