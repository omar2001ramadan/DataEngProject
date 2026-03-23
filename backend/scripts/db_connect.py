"""
Shared database connection helper for build_tables scripts.
Parses DATABASE_URL for psycopg2 and resolves data file paths.
"""
import os
import sys
from urllib.parse import urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from config import DATABASE_URL

# Parse DATABASE_URL into psycopg2 connection params
_parsed = urlparse(DATABASE_URL)
DB_HOST = _parsed.hostname or "localhost"
DB_NAME = _parsed.path.lstrip("/") or "solar_energy"
DB_USER = _parsed.username or "jhu"
DB_PASSWORD = _parsed.password or "jhu123"
DB_PORT = _parsed.port or 5432

# Data directory: backend/data/ inside Docker, or ../data/ locally
DATA_DIR = os.path.join(BACKEND_DIR, "data")
if not os.path.isdir(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "data")


def get_connection():
    import psycopg2
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
    )


def data_file(filename):
    return os.path.join(DATA_DIR, filename)
