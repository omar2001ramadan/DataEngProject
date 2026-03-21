import os
import psycopg2
from dotenv import load_dotenv
"""
Will Gillette
Create renewable_db PostgreSQL database
"""
load_dotenv()
DB_HOST = "localhost"
DB_NAME = "renewable_db"
DB_USER = os.getenv('USERNAME')
DB_PASSWORD = os.getenv('PASSWORD')
DB_PORT = 5432
def create_database():
    # create the renewable_db database
    try:
        # connect to default postgres database
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