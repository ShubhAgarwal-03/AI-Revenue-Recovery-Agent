import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=_uuid)
    batch_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)
    amount_inr = Column(Float, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    decline_code = Column(String, nullable=True)
    gateway_error = Column(String, nullable=True)
    time_of_abandonment_sec = Column(Float, nullable=True)
    context = Column(JSON, default=dict)
    ground_truth_category = Column(String, nullable=True)
    dedup_key = Column(String, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String, primary_key=True, default=_uuid)
    display_id = Column(String, index=True, nullable=True)
    batch_id = Column(String, index=True, nullable=False)
    event_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    is_baseline = Column(Boolean, default=False)

    diagnosed_category = Column(String, nullable=True)
    diagnosis_confidence = Column(Float, nullable=True)
    diagnosis_source = Column(String, nullable=True)

    chosen_action = Column(String, nullable=True)
    policy_confidence = Column(Float, nullable=True)

    gate1_low_confidence_override = Column(Boolean, default=False)
    original_policy_action = Column(String, nullable=True)

    compliance_passed = Column(Boolean, default=False)
    compliance_rejection_reasons = Column(JSON, default=list)

    fallback_action = Column(String, nullable=True)
    fallback_compliance_passed = Column(Boolean, nullable=True)

    executed = Column(Boolean, default=False)
    outcome = Column(String, nullable=True)
    amount_recovered_inr = Column(Float, default=0.0)
    action_cost_inr = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), default=_now)