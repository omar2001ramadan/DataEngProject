import pandas as pd
import psycopg2
from db_connect import get_connection, data_file
"""
Will Gillette
Build PostgreSQL Respondent table from the EIA respondent data CSV
"""
DATA_FILE = data_file("respondent.csv")
TABLE_NAME = "Respondent"

def create_table(conn):
    # create respondent table
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                respondent_id VARCHAR(10) PRIMARY KEY,
                respondent_name VARCHAR(255) NOT NULL,
                region_latitude DECIMAL(10, 8),
                region_longitude DECIMAL(11, 8)
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")

def insert_data(conn):
    # load CSV data into Respondent table
    df = pd.read_csv(DATA_FILE)
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, respondent_name, region_latitude, region_longitude)
                VALUES (%s, %s, %s, %s);
            """, (row["respondent_id"], row["respondent_name"], row.get("latitude"), row.get("longitude")))
        conn.commit()
        print(f"Inserted {len(df)} rows into {TABLE_NAME}.")

def main():
    try:
        conn = get_connection()
        create_table(conn)
        insert_data(conn)
        conn.close()
        print("\nFinished building the PostgreSQL Respondent table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()
