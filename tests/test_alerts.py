from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CheckLog, Endpoint
from app.monitor import should_alert


engine = create_engine("sqlite://")
Session = sessionmaker(bind=engine)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_alerts_after_three_consecutive_failures():
    with Session() as db:
        endpoint = Endpoint(name="API", url="https://api.example.com", interval_seconds=60)
        db.add(endpoint)
        db.commit()
        for _ in range(3):
            check = CheckLog(endpoint_id=endpoint.id, status_code=500, response_time_ms=20)
            db.add(check)
            db.flush()
        assert should_alert(endpoint, check, db) is True


def test_alerts_when_response_exceeds_threshold():
    with Session() as db:
        endpoint = Endpoint(name="API", url="https://api.example.com/slow", interval_seconds=60, response_time_threshold_ms=100)
        db.add(endpoint)
        db.commit()
        check = CheckLog(endpoint_id=endpoint.id, status_code=200, response_time_ms=101)
        db.add(check)
        db.flush()
        assert should_alert(endpoint, check, db) is True
