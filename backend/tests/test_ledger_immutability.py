import pytest
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.models import Base, Decision
from backend.app.db import _install_immutability_trigger


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    _install_immutability_trigger(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def make_decision(db):
    d = Decision(
        batch_id="b1", event_id="e1", customer_id="c1", is_baseline=False,
        chosen_action="retry_now", compliance_passed=True, executed=True,
        outcome="recovered", amount_recovered_inr=100, action_cost_inr=0,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def test_update_is_blocked(db):
    d = make_decision(db)
    d.outcome = "not_recovered"
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()
    db.rollback()


def test_delete_is_blocked(db):
    d = make_decision(db)
    db.delete(d)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db.commit()
    db.rollback()