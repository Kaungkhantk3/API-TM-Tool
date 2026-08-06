import os

os.environ["RUN_SCHEDULER"] = "false"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["AUTH_SECRET"] = "test-secret-that-is-longer-than-thirty-two-characters"

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


def auth_headers():
    response = client.post("/auth/login", json={"username": "admin", "password": "test-password"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_create_endpoint_and_get_summary(monkeypatch):
    monkeypatch.setattr("app.url_safety.socket.getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))])
    headers = auth_headers()
    response = client.post("/endpoints", json={"name": "Example", "url": "https://example.com", "interval_seconds": 60}, headers=headers)
    assert response.status_code == 201
    endpoint = response.json()
    assert endpoint["name"] == "Example"
    summary = client.get("/health-summary", headers=headers)
    assert summary.json() == {"total_endpoints": 1, "healthy_endpoints": 0, "alerting_endpoints": 0, "unchecked_endpoints": 1}


def test_history_requires_existing_endpoint():
    assert client.get("/endpoints/999/history", headers=auth_headers()).status_code == 404


def test_api_requires_login():
    assert client.get("/health-summary").status_code == 401


def test_rejects_private_target():
    response = client.post("/endpoints", json={"name": "Local", "url": "http://127.0.0.1:8000"}, headers=auth_headers())
    assert response.status_code == 422
    assert "Private" in response.json()["detail"]


def test_dashboard_uses_explicit_name_and_url_inputs():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "nameInput.value" in html
    assert "urlInput.value" in html
