import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from db_connect import get_connection
"""
Will Gillette
Build PostgreSQL Date_Dimension table
"""
TABLE_NAME = "Date_Dimension"

def get_season(month):
    # Return season based on month
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    else:
        return "Fall"

def create_table(conn):
    # create Date_Dimension table
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                date_id DATE PRIMARY KEY,
                day_of_week VARCHAR(10),
                month INT,
                month_name VARCHAR(10),
                quarter INT,
                year INT,
                season VARCHAR(10),
                is_weekend BOOLEAN
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")

def insert_data(conn):
    # generate and insert date dimension data
    start_date = datetime(2000, 1, 1)
    end_date = datetime(2030, 12, 31)
    rows = []
    current_date = start_date
    while current_date <= end_date:
        rows.append((
            current_date.date(),
            current_date.strftime("%A"),
            current_date.month,
            current_date.strftime("%B"),
            (current_date.month - 1) // 3 + 1,
            current_date.year,
            get_season(current_date.month),
            current_date.weekday() >= 5
        ))
        current_date += timedelta(days=1)
    with conn.cursor() as cur:
        for row in rows:
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (date_id, day_of_week, month, month_name, quarter, year, season, is_weekend)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, row)
        conn.commit()
        print(f"Inserted {len(rows)} rows into {TABLE_NAME}.")

def main():
    try:
        conn = get_connection()
        create_table(conn)
        insert_data(conn)
        conn.close()
        print("\nFinished building the PostgreSQL Date_Dimension table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()
