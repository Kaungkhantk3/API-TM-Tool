# API Sentinel

API Sentinel periodically calls configured REST endpoints, stores outcomes, exposes a small JSON dashboard API, and flags unhealthy services.

## Run locally

```bash
docker compose up -d db
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
copy .env.example .env
.venv/Scripts/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. For an ephemeral local run, omit `DATABASE_URL`; SQLite is used.

## API

- `POST /endpoints` registers an endpoint.
- `GET /endpoints` lists configured endpoints.
- `GET /endpoints/{id}/history` returns recorded checks.
- `GET /health-summary` reports current health.
- `POST /endpoints/{id}/check` runs a check immediately.

An alert is raised for a response slower than its configured threshold, or after three consecutive non-2xx/error results.

## Railway deployment

1. Create a Railway project from this GitHub repository.
2. Add a PostgreSQL service in that project.
3. Set the API service's `DATABASE_URL` to `${{Postgres.DATABASE_URL}}`, and set `RUN_SCHEDULER=true` for a single API replica.
4. Deploy. Railway assigns `PORT` automatically.

For a scaled production setup, run the scheduler as a separate worker service and set `RUN_SCHEDULER=false` on web replicas.
