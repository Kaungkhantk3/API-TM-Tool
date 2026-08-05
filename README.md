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
