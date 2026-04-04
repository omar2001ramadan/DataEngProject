import pandas as pd
import psycopg2
from db_connect import get_connection, data_file

"""
Will Gillette
Build PostgreSQL Daily_Solar_Timing table from solar timing data
"""

DATA_FILE1 = data_file("sunrise_sunset_CISO.csv")
DATA_FILE2 = data_file("sunrise_sunset_ERCO.csv")
TABLE_NAME = "daily_solar_timing"

def create_table(conn):
    """Create Daily_Solar_Timing table"""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                timing_id SERIAL PRIMARY KEY,
                respondent_id VARCHAR(10) NOT NULL,
                date_id DATE NOT NULL,
                date DATE NOT NULL,
                sunrise TIMESTAMP,
                sunset TIMESTAMP,
                solar_noon TIMESTAMP,
                civil_twilight_begin TIMESTAMP,
                civil_twilight_end TIMESTAMP,
                nautical_twilight_begin TIMESTAMP,
                nautical_twilight_end TIMESTAMP,
                astronomical_twilight_begin TIMESTAMP,
                astronomical_twilight_end TIMESTAMP,
                FOREIGN KEY (respondent_id) REFERENCES respondent(respondent_id),
                UNIQUE (respondent_id, date)
            );
        """)
        conn.commit()
        print(f"Table {TABLE_NAME} created successfully.")

def insert_data(conn):
    """Load CSV data into Daily_Solar_Timing table"""
    df1 = pd.read_csv(DATA_FILE1)
    df2 = pd.read_csv(DATA_FILE2)

    with conn.cursor() as cur:
        for _, row in df1.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, date_id, date, sunrise, sunset, solar_noon,
                                          civil_twilight_begin, civil_twilight_end, nautical_twilight_begin,
                                          nautical_twilight_end, astronomical_twilight_begin, astronomical_twilight_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, ('CISO', row["date"], row["date"], row.get("sunrise"), row.get("sunset"),
                  row.get("solar_noon"), row.get("civil_twilight_begin"),
                  row.get("civil_twilight_end"), row.get("nautical_twilight_begin"),
                  row.get("nautical_twilight_end"), row.get("astronomical_twilight_begin"),
                  row.get("astronomical_twilight_end")))
        conn.commit()
        print(f"Inserted {len(df1)} CISO rows into {TABLE_NAME}.")
        for _, row in df2.iterrows():
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (respondent_id, date_id, date, sunrise, sunset, solar_noon,
                                          civil_twilight_begin, civil_twilight_end, nautical_twilight_begin,
                                          nautical_twilight_end, astronomical_twilight_begin, astronomical_twilight_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, ('ERCO', row["date"], row["date"], row.get("sunrise"), row.get("sunset"),
                  row.get("solar_noon"), row.get("civil_twilight_begin"),
                  row.get("civil_twilight_end"), row.get("nautical_twilight_begin"),
                  row.get("nautical_twilight_end"), row.get("astronomical_twilight_begin"),
                  row.get("astronomical_twilight_end")))
        conn.commit()
        print(f"Inserted {len(df2)} ERCO rows into {TABLE_NAME}.")

def main():
    try:
        conn = get_connection()
        create_table(conn)
        insert_data(conn)
        conn.close()
        print("\nFinished building the PostgreSQL daily_solar_timing table")
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    main()
