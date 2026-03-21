import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
"""
Will Gillette
Build PostgreSQL Weather Station table from the EIA station data CSV
"""
# Database connection parameters    
load_dotenv()
DB_HOST = "localhost"
DB_NAME = "renewable_db"
DB_USER = os.getenv('USERNAME')
DB_PASSWORD = os.getenv('PASSWORD')
DB_PORT = 5432
DATA_FILE = "../data/weather_station.csv"
TABLE_NAME = "Weather_Station"
def create_table(conn):
    # build weather station table using burch's schema
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                station_id VARCHAR(50) PRIMARY KEY,
                station_name VARCHAR(255) NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                respondent_id VARCHAR(10) NOT NULL,
                FOREIGN KEY (respondent_id) REFERENCES Respondent(respondent_id)
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")

def insert_data(conn):
    # load CSV data into Weather_Station table
    df = pd.read_csv(DATA_FILE)
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (station_id, station_name, latitude, longitude, respondent_id)
                VALUES (%s, %s, %s, %s, %s);
            """, (row["station_id"], row["station_name"], row.get("latitude"), row.get("longitude"), row["respondent_id"]))
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
        print("\nFinished building the PostgreSQL Weather_Station table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()