from sqlalchemy.orm import Session

from backend.app.models import Decision


def build_exceptions(db: Session, batch_id: str) -> list[dict]:
    decisions = (
        db.query(Decision)
        .filter(
            Decision.batch_id == batch_id,
            Decision.is_baseline == False,  # noqa: E712
            Decision.executed == False,  # noqa: E712
        )
        .all()
    )
    result = []
    for d in decisions:
        result.append({
            "event_id": d.event_id,
            "category": d.diagnosed_category,
            "attempted_action": d.chosen_action,
            "gate1_low_confidence_override": d.gate1_low_confidence_override,
            "compliance_rejection_reasons": d.compliance_rejection_reasons or [],
            "fallback_action": d.fallback_action,
            "fallback_compliance_passed": d.fallback_compliance_passed,
        })
    return result