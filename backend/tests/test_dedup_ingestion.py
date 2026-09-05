from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from backend.app.models import Base, Event
from backend.app.detector.ingest import ingest_events


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_duplicate_event_in_same_call_only_creates_one_row(db):
    raw = {
        "event_type": "payment_failure",
        "amount_inr": 1000,
        "customer_id": "cust_1",
        "decline_code": "insufficient_funds",
        "gateway_error": None,
        "context": {},
    }
    inserted, inserted_count, skipped_count = ingest_events(db, "batch_dup", [raw, raw])
    assert inserted_count == 1
    assert skipped_count == 1
    assert db.query(Event).filter(Event.batch_id == "batch_dup").count() == 1


def test_duplicate_event_across_calls_is_skipped(db):
    raw = {
        "event_type": "payment_failure",
        "amount_inr": 1000,
        "customer_id": "cust_1",
        "decline_code": "insufficient_funds",
        "gateway_error": None,
        "context": {},
    }
    ingest_events(db, "batch_dup2", [raw])
    inserted, inserted_count, skipped_count = ingest_events(db, "batch_dup2", [raw])
    assert inserted_count == 0
    assert skipped_count == 1
    assert db.query(Event).filter(Event.batch_id == "batch_dup2").count() == 1


def test_distinct_events_are_both_inserted(db):
    raw1 = {"event_type": "payment_failure", "amount_inr": 1000, "customer_id": "cust_1",
            "decline_code": "insufficient_funds", "gateway_error": None, "context": {}}
    raw2 = {"event_type": "payment_failure", "amount_inr": 2000, "customer_id": "cust_2",
            "decline_code": "do_not_honor", "gateway_error": None, "context": {}}
    inserted, inserted_count, skipped_count = ingest_events(db, "batch_dup3", [raw1, raw2])
    assert inserted_count == 2
    assert skipped_count == 0