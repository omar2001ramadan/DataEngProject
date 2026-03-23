import psycopg2
from db_connect import DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME
"""
Will Gillette
Create PostgreSQL database
"""
def create_database():
    # create the database
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database {DB_NAME} created successfully.")
        conn.close()
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        raise

if __name__ == "__main__":
    create_database()
