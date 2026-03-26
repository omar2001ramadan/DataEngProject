"""
Burch Parshall
Build PostgreSQL solar_capacity table to track installed solar capacity (MW)
by region over time, sourced from the EIA operating generator capacity API.
"""
import pandas as pd
import psycopg2
from db_connect import get_connection, data_file

TABLE_NAME = "solar_capacity"
DATA_FILE = data_file("eia_capacity_monthly.csv")


def create_table(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                capacity_id SERIAL PRIMARY KEY,
                respondent_id VARCHAR(10) NOT NULL REFERENCES respondent(respondent_id),
                date_id DATE NOT NULL REFERENCES date_dimension(date_id),
                capacity_mw DECIMAL(15, 3) NOT NULL,
                UNIQUE (respondent_id, date_id)
            );
        """)
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_capacity_respondent_date
            ON {TABLE_NAME}(respondent_id, date_id);
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")


def insert_data(conn):
    df = pd.read_csv(DATA_FILE)
    df["date_id"] = pd.to_datetime(df["date_id"]).dt.date
    df["capacity_mw"] = pd.to_numeric(df["capacity_mw"], errors="coerce")
    df = df.dropna(subset=["respondent_id", "date_id", "capacity_mw"])
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, date_id, capacity_mw)
                VALUES (%s, %s, %s)
                ON CONFLICT (respondent_id, date_id) DO NOTHING;
            """, (row["respondent_id"], row["date_id"], row["capacity_mw"]))
        conn.commit()
        print(f"Inserted {len(df)} rows into {TABLE_NAME}.")


def main():
    try:
        conn = get_connection()
        create_table(conn)
        insert_data(conn)
        conn.close()
        print(f"\nFinished building the PostgreSQL {TABLE_NAME} table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise


if __name__ == "__main__":
    main()
