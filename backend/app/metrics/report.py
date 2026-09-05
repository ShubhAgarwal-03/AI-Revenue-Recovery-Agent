import re
from collections import defaultdict

from sqlalchemy.orm import Session

from backend.app.models import Decision
from backend.app.config import Action, FailureCategory


def _bucket_reason(reason: str) -> str:
    """Bucket a rejection reason string by its stable prefix (before any
    parenthetical dynamic detail), so e.g. 'contact_limit_exceeded (3 >= 3)'
    and 'contact_limit_exceeded (5 >= 3)' both bucket as 'contact_limit_exceeded'.
    """
    return re.split(r"\s*\(", reason, maxsplit=1)[0]


def build_metrics_report(db: Session, batch_id: str) -> dict:
    agent_decisions = (
        db.query(Decision)
        .filter(Decision.batch_id == batch_id, Decision.is_baseline == False)  # noqa: E712
        .all()
    )
    baseline_decisions = (
        db.query(Decision)
        .filter(Decision.batch_id == batch_id, Decision.is_baseline == True)  # noqa: E712
        .all()
    )

    total_events = len(agent_decisions)
    recovered = sum(1 for d in agent_decisions if d.outcome == "recovered")
    recovery_rate = (recovered / total_events) if total_events else 0.0

    agent_recovered_inr = sum(d.amount_recovered_inr or 0.0 for d in agent_decisions)
    baseline_recovered_inr = sum(d.amount_recovered_inr or 0.0 for d in baseline_decisions)
    lift_inr = agent_recovered_inr - baseline_recovered_inr

    rejection_reason_counts = defaultdict(int)
    compliance_rejections = 0
    for d in agent_decisions:
        reasons = d.compliance_rejection_reasons or []
        if reasons:
            compliance_rejections += 1
            for r in reasons:
                rejection_reason_counts[_bucket_reason(r)] += 1

    false_escalation_count = sum(
        1 for d in agent_decisions
        if d.chosen_action == Action.HUMAN_ESCALATION.value
        and not d.gate1_low_confidence_override
        and d.diagnosed_category != FailureCategory.WILLFUL_NON_PAYMENT.value
    )

    gate1_overrides = sum(1 for d in agent_decisions if d.gate1_low_confidence_override)

    fallback_used = sum(1 for d in agent_decisions if d.fallback_action)
    # Graceful-degradation success: did the fallback pass Gate 2 and get
    # executed at all? This is distinct from whether it recovered money.
    fallback_executed = sum(
        1 for d in agent_decisions
        if d.fallback_action and d.fallback_compliance_passed
    )
    # Money-recovery success specifically via the fallback path.
    fallback_recovered_money = sum(
        1 for d in agent_decisions
        if d.fallback_action and d.fallback_compliance_passed and d.outcome == "recovered"
    )

    return {
        "batch_id": batch_id,
        "recovery_rate": recovery_rate,
        "agent_recovered_inr": agent_recovered_inr,
        "baseline_recovered_inr": baseline_recovered_inr,
        "lift_inr": lift_inr,
        "compliance_rejections": compliance_rejections,
        "compliance_rejection_reasons": dict(rejection_reason_counts),
        "false_escalation_count": false_escalation_count,
        "gate1_low_confidence_overrides": gate1_overrides,
        "fallback_actions_used": fallback_used,
        "fallback_actions_executed": fallback_executed,
        "fallback_actions_recovered_money": fallback_recovered_money,
    }
