from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, Event
from backend.app.pipeline import process_event_agent
from backend.app.config import settings, Action


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def widen_contact_hours():
    old_start, old_end, old_cooldown = (
        settings.contact_hours_start, settings.contact_hours_end, settings.contact_cooldown_hours,
    )
    settings.contact_hours_start = 0
    settings.contact_hours_end = 24
    settings.contact_cooldown_hours = 0
    yield
    settings.contact_hours_start, settings.contact_hours_end, settings.contact_cooldown_hours = (
        old_start, old_end, old_cooldown,
    )


def make_event(db, event_type="payment_failure", decline_code="unknown_code_zz", customer_id="cust_1", context=None):
    e = Event(batch_id="b1", event_type=event_type, amount_inr=1000, customer_id=customer_id,
               decline_code=decline_code, context=context or {})
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_gate1_override_forces_human_escalation_on_low_confidence(db):
    e = make_event(db, decline_code="totally_unknown_code")
    decision = process_event_agent(db, e)
    assert decision.gate1_low_confidence_override is True
    assert decision.chosen_action == Action.HUMAN_ESCALATION.value
    assert decision.original_policy_action is not None


def test_gate1_no_override_on_high_confidence(db):
    e = make_event(db, decline_code="insufficient_funds")
    decision = process_event_agent(db, e)
    assert decision.gate1_low_confidence_override is False


def test_gate2_rejection_falls_back_gracefully(db):
    e = make_event(db, event_type="checkout_abandonment", decline_code=None,
                     context={"opted_out": True})
    decision = process_event_agent(db, e)
    assert decision.fallback_action == Action.RETRY_IN_24H.value
    assert decision.fallback_compliance_passed is True
    assert decision.executed is True


def test_gate2_rejection_with_no_viable_fallback_logs_unresolved_exception(db):
    old_ceiling = settings.spend_ceiling_inr
    settings.spend_ceiling_inr = -1
    try:
        e = make_event(db, decline_code="do_not_honor")  # -> hard_decline
        decision = process_event_agent(db, e)
        assert decision.executed is False
        assert decision.compliance_passed is False
    finally:
        settings.spend_ceiling_inr = old_ceiling