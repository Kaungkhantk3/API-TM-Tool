import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api_sentinel.db")
# Railway exposes a standard PostgreSQL URL; SQLAlchemy uses this driver name.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "true").lower() == "true"
SCHEDULER_TICK_SECONDS = int(os.getenv("SCHEDULER_TICK_SECONDS", "30"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
AUTH_SECRET = os.getenv("AUTH_SECRET", "")
