from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Decision


def next_display_id(db: Session) -> str:
    count = db.query(func.count(Decision.id)).scalar() or 0
    return f"DEC-{count + 1:06d}"


def record_decision(db: Session, **kwargs) -> Decision:
    kwargs["display_id"] = next_display_id(db)
    decision = Decision(**kwargs)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def decision_to_dict(d: Decision) -> dict:
    return {
        "id": d.display_id or d.id,
        "internal_id": d.id,
        "batch_id": d.batch_id,
        "event_id": d.event_id,
        "customer_id": d.customer_id,
        "is_baseline": d.is_baseline,
        "diagnosed_category": d.diagnosed_category,
        "diagnosis_confidence": d.diagnosis_confidence,
        "diagnosis_source": d.diagnosis_source,
        "chosen_action": d.chosen_action,
        "policy_confidence": d.policy_confidence,
        "gate1_low_confidence_override": d.gate1_low_confidence_override,
        "original_policy_action": d.original_policy_action,
        "compliance_passed": d.compliance_passed,
        "compliance_rejection_reasons": d.compliance_rejection_reasons or [],
        "fallback_action": d.fallback_action,
        "fallback_compliance_passed": d.fallback_compliance_passed,
        "executed": d.executed,
        "outcome": d.outcome,
        "amount_recovered_inr": d.amount_recovered_inr,
        "action_cost_inr": d.action_cost_inr,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }