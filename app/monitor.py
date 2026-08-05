from datetime import datetime, timezone
from time import perf_counter

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CheckLog, Endpoint


def _is_failure(check: CheckLog) -> bool:
    return check.status_code is None or not 200 <= check.status_code < 300


def should_alert(endpoint: Endpoint, check: CheckLog, db: Session) -> bool:
    if endpoint.response_time_threshold_ms and check.response_time_ms:
        if check.response_time_ms > endpoint.response_time_threshold_ms:
            return True
    recent = db.scalars(
        select(CheckLog).where(CheckLog.endpoint_id == endpoint.id).order_by(CheckLog.id.desc()).limit(3)
    ).all()
    return len(recent) == 3 and all(_is_failure(item) for item in recent)


def check_endpoint(endpoint: Endpoint, db: Session, client: httpx.Client | None = None) -> CheckLog:
    started = perf_counter()
    status_code = None
    error_message = None
    request_client = client or httpx.Client(follow_redirects=True)
    try:
        response = request_client.get(endpoint.url, timeout=endpoint.timeout_seconds)
        status_code = response.status_code
    except httpx.HTTPError as exc:
        error_message = str(exc)
    finally:
        if client is None:
            request_client.close()
    elapsed_ms = round((perf_counter() - started) * 1000)
    check = CheckLog(endpoint_id=endpoint.id, status_code=status_code, response_time_ms=elapsed_ms, error_message=error_message)
    db.add(check)
    db.flush()
    check.is_alert = should_alert(endpoint, check, db)
    db.commit()
    db.refresh(check)
    return check


def endpoint_is_due(endpoint: Endpoint, db: Session) -> bool:
    latest = db.scalar(select(CheckLog).where(CheckLog.endpoint_id == endpoint.id).order_by(CheckLog.id.desc()))
    if latest is None:
        return True
    checked_at = latest.checked_at.replace(tzinfo=timezone.utc) if latest.checked_at.tzinfo is None else latest.checked_at
    return (datetime.now(timezone.utc) - checked_at).total_seconds() >= endpoint.interval_seconds


def run_due_checks(db: Session) -> None:
    for endpoint in db.scalars(select(Endpoint).where(Endpoint.active.is_(True))).all():
        if endpoint_is_due(endpoint, db):
            check_endpoint(endpoint, db)
