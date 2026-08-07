# API Sentinel

API Sentinel is a lightweight endpoint monitoring service built with FastAPI. It periodically checks configured REST endpoints, stores check history, and exposes a dashboard/API for monitoring service health.
<img width="1434" height="682" alt="image" src="https://github.com/user-attachments/assets/b5450657-3a7e-4217-b438-ba0ad7c09b89" />
<img width="1433" height="679" alt="image" src="https://github.com/user-attachments/assets/199d19bf-9549-4b61-b07e-e9a4bd3d2bc9" />



## Features

- Register and manage monitored HTTP/HTTPS endpoints
- Run checks on a schedule or manually on demand
- Store status code, response time, and error details per check
- Alert on:
  - response time threshold breaches
  - three consecutive failed checks (non-2xx or request error)
- Dashboard UI and JSON API
- Single-admin token authentication
- URL safety protections to block private/internal targets

## Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- APScheduler
- HTTPX
- Pydantic
- PostgreSQL (production) or SQLite (local fallback)
- Pytest

## Project structure

```text
app/
  main.py         # FastAPI app, routes, scheduler startup
  monitor.py      # Endpoint check + alert logic
  models.py       # SQLAlchemy models (Endpoint, CheckLog)
  schemas.py      # Pydantic request/response schemas
  security.py     # Admin auth + signed bearer tokens
  url_safety.py   # Public URL validation / SSRF protections
  database.py     # Engine/session setup and DB dependency
  config.py       # Environment-based configuration
  static/
    index.html    # Web dashboard
tests/
  test_api.py
  test_alerts.py
  test_url_safety.py
```

## Configuration

Copy `.env.example` to `.env` and set:

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `AUTH_SECRET` (at least 32 random characters)

Optional:

- `DATABASE_URL` (if omitted, SQLite `api_sentinel.db` is used)
- `RUN_SCHEDULER` (`true`/`false`)
- `SCHEDULER_TICK_SECONDS` (default `30`)

## Running locally

### Option 1: quick local run (SQLite)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env       # Windows PowerShell: copy .env.example .env
uvicorn app.main:app --reload
```

### Option 2: local Postgres with Docker Compose

```bash
docker compose up -d db
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Open:

- Dashboard: `http://127.0.0.1:8000/`
- API docs: `http://127.0.0.1:8000/docs`

## API overview

### Authentication

- `POST /auth/login` → returns bearer token
- `GET /auth/me` → validates current token

### Endpoints

- `POST /endpoints` → create monitor
- `GET /endpoints` → list monitors
- `POST /endpoints/{id}/check` → run immediate check
- `GET /endpoints/{id}/history` → check history
- `GET /health-summary` → aggregate status counts
- `GET /dashboard-data` → dashboard payload

## Security notes

- The app is single-admin by design.
- Do not deploy with sample credentials from `.env.example`.
- Only public `http`/`https` targets are allowed.
- Localhost, private, loopback, link-local, and reserved IP ranges are rejected.
- Redirects are disabled during checks.

## Testing

```bash
pytest
```

## Docker

Build and run:

```bash
docker build -t api-sentinel .
docker run --rm -p 8000:8000 --env-file .env api-sentinel
```

## Railway deployment

1. Create a Railway project from this repository.
2. Add a PostgreSQL service.
3. Set:
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
   - `ADMIN_USERNAME`
   - `ADMIN_PASSWORD` (strong value)
   - `AUTH_SECRET` (32+ random characters)
4. For a single API replica, set `RUN_SCHEDULER=true`.
5. Deploy (Railway sets `PORT` automatically).

For scaled deployments, run scheduler in one dedicated service and set `RUN_SCHEDULER=false` on web replicas.
