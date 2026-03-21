from ast import Load
import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
"""
Will Gillette
Build PostgreSQL Weather_Observation table from weather data CSV
"""
# Database connection parameters    
load_dotenv()
DB_HOST = "localhost"
DB_NAME = "renewable_db"
DB_USER = os.getenv('USERNAME')
DB_PASSWORD = os.getenv('PASSWORD')
DB_PORT = 5432
DATA_FILE = "../data/weather_observation.csv"
TABLE_NAME = "Weather_Observation"
def create_table(conn):
    # create weather observation table
    with conn.cursor() as cur:
        cur.execute(f"""
            DROP TABLE IF EXISTS {TABLE_NAME};""")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                observation_id SERIAL PRIMARY KEY,
                station_id VARCHAR(50),
                date_id DATE,
                observation_datetime TIMESTAMP,
                dry_bulb_temp_c DECIMAL(5, 2),
                dew_point_temp_c DECIMAL(5, 2),
                relative_humidity_pct DECIMAL(5, 2),
                wet_bulb_temp_c DECIMAL(5, 2),
                wind_speed_kmh DECIMAL(6, 2),
                wind_direction_deg INT,
                wind_gust_speed_kmh DECIMAL(6, 2),
                precipitation_mm DECIMAL(8, 2),
                sky_conditions VARCHAR(100),
                visibility_km DECIMAL(6, 2),
                station_pressure_hpa DECIMAL(7, 2),
                altimeter_setting_hpa DECIMAL(7, 2),
                FOREIGN KEY (station_id) REFERENCES Weather_Station(station_id),
                FOREIGN KEY (date_id) REFERENCES Date_Dimension(date_id)
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")
def insert_data(conn):
    # load CSV data into Weather_Observation table
    df = pd.read_csv(DATA_FILE, dtype={"station_id": str,"wind_direction_deg": "Int64"})
    df = df.astype(object).where(df.notnull(), None)
    df["date_id"] = pd.to_datetime(df["observation_datetime"]).dt.date
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (station_id, date_id, observation_datetime, dry_bulb_temp_c, 
                dew_point_temp_c, relative_humidity_pct, wet_bulb_temp_c, wind_speed_kmh, wind_direction_deg, 
                wind_gust_speed_kmh, precipitation_mm, sky_conditions, visibility_km, station_pressure_hpa, altimeter_setting_hpa)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (row["station_id"], row["date_id"], row["observation_datetime"], row.get("dry_bulb_temp_c"),
                  row.get("dew_point_temp_c"), row.get("relative_humidity_pct"), row.get("wet_bulb_temp_c"),
                  row.get("wind_speed_kmh"), row.get("wind_direction_deg"), row.get("wind_gust_speed_kmh"),
                  row.get("precipitation_mm"), row.get("sky_conditions"), row.get("visibility_km"),
                  row.get("station_pressure_hpa"), row.get("altimeter_setting_hpa")))
        conn.commit()
        print(f"Inserted {len(df)} rows into {TABLE_NAME}.")

def main():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        create_table(conn)
        insert_data(conn)        
        conn.close()
        print("\nFinished building the PostgreSQL Weather_Observation table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()