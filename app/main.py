from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import RUN_SCHEDULER, SCHEDULER_TICK_SECONDS
from app.database import Base, SessionLocal, engine, get_db
from app.models import CheckLog, Endpoint
from app.monitor import check_endpoint, run_due_checks
from app.schemas import CheckOut, EndpointCreate, EndpointOut, HealthSummary


def scheduled_run() -> None:
    with SessionLocal() as db:
        run_due_checks(db)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    scheduler = BackgroundScheduler() if RUN_SCHEDULER else None
    if scheduler:
        scheduler.add_job(scheduled_run, "interval", seconds=SCHEDULER_TICK_SECONDS, id="endpoint-checks")
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="API Sentinel", version="0.1.0", lifespan=lifespan)


@app.post("/endpoints", response_model=EndpointOut, status_code=status.HTTP_201_CREATED)
def create_endpoint(payload: EndpointCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Endpoint).where(Endpoint.url == str(payload.url))):
        raise HTTPException(status_code=409, detail="Endpoint URL is already monitored")
    endpoint = Endpoint(**payload.model_dump(mode="json"))
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@app.get("/endpoints", response_model=list[EndpointOut])
def list_endpoints(db: Session = Depends(get_db)):
    return db.scalars(select(Endpoint).order_by(Endpoint.id)).all()


@app.post("/endpoints/{endpoint_id}/check", response_model=CheckOut)
def run_check(endpoint_id: int, db: Session = Depends(get_db)):
    endpoint = db.get(Endpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return check_endpoint(endpoint, db)


@app.get("/endpoints/{endpoint_id}/history", response_model=list[CheckOut])
def history(endpoint_id: int, limit: int = 50, db: Session = Depends(get_db)):
    if db.get(Endpoint, endpoint_id) is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return db.scalars(
        select(CheckLog).where(CheckLog.endpoint_id == endpoint_id).order_by(CheckLog.id.desc()).limit(min(limit, 200))
    ).all()


@app.get("/health-summary", response_model=HealthSummary)
def health_summary(db: Session = Depends(get_db)):
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
