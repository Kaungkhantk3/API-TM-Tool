import os

os.environ["RUN_SCHEDULER"] = "false"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import CheckLog


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)


def override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_db
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_create_endpoint_and_get_summary():
    response = client.post("/endpoints", json={"name": "Example", "url": "https://example.com", "interval_seconds": 60})
    assert response.status_code == 201
    endpoint = response.json()
    assert endpoint["name"] == "Example"
    summary = client.get("/health-summary")
    assert summary.json() == {"total_endpoints": 1, "healthy_endpoints": 0, "alerting_endpoints": 0, "unchecked_endpoints": 1}


def test_history_requires_existing_endpoint():
    assert client.get("/endpoints/999/history").status_code == 404

