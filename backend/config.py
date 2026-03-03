import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://localhost:5432/solar_energy"
)

# Railway uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
