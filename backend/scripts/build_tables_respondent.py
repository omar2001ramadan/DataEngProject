import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
"""
Will Gillette
Build PostgreSQL Respondent table from the EIA respondent data CSV
"""
# Database connection parameters    
load_dotenv()
DB_HOST = "localhost"
DB_NAME = "renewable_db"
DB_USER = os.getenv('USERNAME')
DB_PASSWORD = os.getenv('PASSWORD')
DB_PORT = 5432
DATA_FILE = "../data/respondent.csv"
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
            print(row)
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, respondent_name, region_latitude, region_longitude)
                VALUES (%s, %s, %s, %s);
            """, (row["respondent_id"], row["respondent_name"], row.get("latitude"), row.get("longitude")))
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
        print("\nFinished building the PostgreSQL Respondent table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()