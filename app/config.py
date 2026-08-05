import os


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api_sentinel.db")
RUN_SCHEDULER = os.getenv("RUN_SCHEDULER", "true").lower() == "true"
SCHEDULER_TICK_SECONDS = int(os.getenv("SCHEDULER_TICK_SECONDS", "30"))
