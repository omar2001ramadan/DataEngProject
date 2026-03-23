import pandas as pd
import psycopg2
from db_connect import get_connection, data_file
"""
Will Gillette
build PostgreSQL Solar_Generation table from the EIA solar data CSV
"""
DATA_FILE = data_file("eia_solar_hourly.csv")
TABLE_NAME = "Solar_Generation"

def create_table(conn):
    # create a solar generation table using burch's schema
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                generation_id SERIAL PRIMARY KEY,
                respondent_id VARCHAR(10) NOT NULL REFERENCES Respondent(respondent_id),
                period TIMESTAMP NOT NULL,
                date_id DATE NOT NULL REFERENCES Date_Dimension(date_id),
                value_mwh DECIMAL(15, 3) NOT NULL
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")

def insert_data(conn):
    # load CSV data into Solar_Generation table
    df = pd.read_csv(DATA_FILE)
    # convert period to datetime if not already
    df["period"] = pd.to_datetime(df["period"])
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, period, date_id, value_mwh)
                VALUES (%s, %s, %s, %s);
            """, (row["respondent"], row["period"], row["period"].date(), row["value"]))
        conn.commit()
        print(f"Inserted {len(df)} rows into {TABLE_NAME}.")

def main():
    try:
        conn = get_connection()
        create_table(conn)
        insert_data(conn)
        conn.close()
        print("\nFinished building the PostgreSQL Solar_Generation table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()
