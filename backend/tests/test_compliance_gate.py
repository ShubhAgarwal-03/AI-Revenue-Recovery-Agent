from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, Event, Decision
from backend.app.compliance import gate
from backend.app.config import Action, settings


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def make_event(db, customer_id="cust_1", opted_out=False):
    e = Event(batch_id="b1", event_type="payment_failure", amount_inr=1000,
               customer_id=customer_id, context={"opted_out": opted_out})
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_opt_out_blocks(db):
    e = make_event(db, opted_out=True)
    now = datetime.now(timezone.utc).replace(hour=12)
    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert not passed
    assert any("opted_out" in r for r in reasons)


def test_contact_hours_blocks(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=3)
    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert not passed
    assert any("outside_contact_hours" in r for r in reasons)


def test_contact_hours_passes_within_window(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert passed
    assert reasons == []


def test_spend_ceiling_blocks(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    old_ceiling = settings.spend_ceiling_inr
    settings.spend_ceiling_inr = 10
    try:
        passed, reasons = gate.evaluate(db, e, Action.HUMAN_ESCALATION, now=now)
        assert not passed
        assert any("spend_ceiling_exceeded" in r for r in reasons)
    finally:
        settings.spend_ceiling_inr = old_ceiling


def test_cooldown_blocks_recent_contact(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    d = Decision(
        batch_id="b1", event_id=e.id, customer_id=e.customer_id, is_baseline=False,
        chosen_action=Action.SMS_NUDGE.value, compliance_passed=True, executed=True,
        outcome="recovered", amount_recovered_inr=100, action_cost_inr=0.5,
        created_at=now - timedelta(hours=1),
    )
    db.add(d)
    db.commit()

    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert not passed
    assert any("cooldown_active" in r for r in reasons)


def test_cooldown_handles_tz_naive_timestamp(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    naive_recent = (now - timedelta(hours=1)).replace(tzinfo=None)
    d = Decision(
        batch_id="b1", event_id=e.id, customer_id=e.customer_id, is_baseline=False,
        chosen_action=Action.SMS_NUDGE.value, compliance_passed=True, executed=True,
        outcome="recovered", amount_recovered_inr=100, action_cost_inr=0.5,
        created_at=naive_recent,
    )
    db.add(d)
    db.commit()

    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert not passed
    assert any("cooldown_active" in r for r in reasons)


def test_cooldown_passes_after_window(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    d = Decision(
        batch_id="b1", event_id=e.id, customer_id=e.customer_id, is_baseline=False,
        chosen_action=Action.SMS_NUDGE.value, compliance_passed=True, executed=True,
        outcome="recovered", amount_recovered_inr=100, action_cost_inr=0.5,
        created_at=now - timedelta(hours=25),
    )
    db.add(d)
    db.commit()

    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert passed
    assert reasons == []


def test_contact_limit_blocks_after_max(db):
    e = make_event(db)
    now = datetime.now(timezone.utc).replace(hour=12)
    for _ in range(settings.max_contacts_per_customer_per_window):
        d = Decision(
            batch_id="b1", event_id=e.id, customer_id=e.customer_id, is_baseline=False,
            chosen_action=Action.SMS_NUDGE.value, compliance_passed=True, executed=True,
            outcome="not_recovered", amount_recovered_inr=0, action_cost_inr=0.5,
            created_at=now - timedelta(days=10),
        )
        db.add(d)
    db.commit()

    passed, reasons = gate.evaluate(db, e, Action.SMS_NUDGE, now=now)
    assert not passed
    assert any("contact_limit_exceeded" in r for r in reasons)