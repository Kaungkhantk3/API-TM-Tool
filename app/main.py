from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import RUN_SCHEDULER, SCHEDULER_TICK_SECONDS
from app.database import Base, SessionLocal, engine, get_db
from app.models import CheckLog, Endpoint
from app.monitor import check_endpoint, run_due_checks
from app.schemas import (
    CheckOut, DashboardData, DashboardEndpoint, EndpointCreate, EndpointOut,
    HealthSummary, LoginRequest, TokenResponse,
)
from app.security import authenticate, create_access_token, get_current_user, validate_auth_config
from app.url_safety import validate_public_url

STATIC_DIR = Path(__file__).parent / "static"


def scheduled_run() -> None:
    with SessionLocal() as db:
        run_due_checks(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_auth_config()
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler() if RUN_SCHEDULER else None
    if scheduler:
        scheduler.add_job(scheduled_run, "interval", seconds=SCHEDULER_TICK_SECONDS, id="endpoint-checks")
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="API Sentinel", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def dashboard_page():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/auth/login", response_model=TokenResponse, tags=["authentication"])
def login(payload: LoginRequest):
    if not authenticate(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return TokenResponse(access_token=create_access_token(payload.username))


@app.get("/auth/me", tags=["authentication"])
def current_user(username: str = Depends(get_current_user)):
    return {"username": username}


@app.post("/endpoints", response_model=EndpointOut, status_code=status.HTTP_201_CREATED)
def create_endpoint(payload: EndpointCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    try:
        validate_public_url(str(payload.url))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    if db.scalar(select(Endpoint).where(Endpoint.url == str(payload.url))):
        raise HTTPException(status_code=409, detail="Endpoint URL is already monitored")
    endpoint = Endpoint(**payload.model_dump(mode="json"))
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@app.get("/endpoints", response_model=list[EndpointOut])
def list_endpoints(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return db.scalars(select(Endpoint).order_by(Endpoint.id)).all()


@app.post("/endpoints/{endpoint_id}/check", response_model=CheckOut)
def run_check(endpoint_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    endpoint = db.get(Endpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return check_endpoint(endpoint, db)


@app.get("/endpoints/{endpoint_id}/history", response_model=list[CheckOut])
def history(endpoint_id: int, limit: int = 50, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    if db.get(Endpoint, endpoint_id) is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return db.scalars(
        select(CheckLog).where(CheckLog.endpoint_id == endpoint_id).order_by(CheckLog.id.desc()).limit(min(limit, 200))
    ).all()


@app.get("/health-summary", response_model=HealthSummary)
def health_summary(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    return build_health_summary(db)


def build_health_summary(db: Session) -> HealthSummary:
    endpoints = db.scalars(select(Endpoint).where(Endpoint.active.is_(True))).all()
    alerting = 0
    unchecked = 0
    for endpoint in endpoints:
        latest = db.scalar(select(CheckLog).where(CheckLog.endpoint_id == endpoint.id).order_by(CheckLog.id.desc()))
        if latest is None:
            unchecked += 1
        elif latest.is_alert:
            alerting += 1
    return HealthSummary(total_endpoints=len(endpoints), healthy_endpoints=len(endpoints) - alerting - unchecked,
                         alerting_endpoints=alerting, unchecked_endpoints=unchecked)


@app.get("/dashboard-data", response_model=DashboardData, include_in_schema=False)
def dashboard_data(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    cards = []
    for endpoint in db.scalars(select(Endpoint).where(Endpoint.active.is_(True)).order_by(Endpoint.id)).all():
        latest = db.scalar(select(CheckLog).where(CheckLog.endpoint_id == endpoint.id).order_by(CheckLog.id.desc()))
        cards.append(DashboardEndpoint(
            id=endpoint.id, name=endpoint.name, url=endpoint.url,
            status_code=latest.status_code if latest else None,
            response_time_ms=latest.response_time_ms if latest else None,
            is_alert=latest.is_alert if latest else False,
        ))
    return DashboardData(summary=build_health_summary(db), endpoints=cards)
