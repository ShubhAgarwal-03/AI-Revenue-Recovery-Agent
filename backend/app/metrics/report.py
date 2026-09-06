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


def _compute_escalation_breakdown(agent_decisions: list[Decision]) -> dict:
    """
    Splits human_escalation decisions into three buckets instead of one
    lumped 'false_escalation_count':

      - low_confidence_escalations: Gate 1 overrode a low-confidence
        diagnosis into human_escalation. These are hedges, not mistakes --
        the system is paying a bounded cost (escalation) instead of betting
        on an automated action it isn't confident will work.
      - expected_escalations: category is willful_non_payment, where
        human_escalation is the designed default action for that category.
      - high_value_policy_escalations: the policy chose human_escalation on
        its own (no Gate 1 override) for a non-willful category. Usually
        means the expected-value math favored a human follow-up over an
        automated retry for a high-value transaction -- a deliberate
        economic call, not a "false" escalation.

    Only agent decisions are considered; baseline decisions never escalate.
    """
    low_confidence_escalations = 0
    expected_escalations = 0
    high_value_policy_escalations = 0

    for d in agent_decisions:
        if d.chosen_action != Action.HUMAN_ESCALATION.value:
            continue

        if d.gate1_low_confidence_override:
            low_confidence_escalations += 1
        elif d.diagnosed_category == FailureCategory.WILLFUL_NON_PAYMENT.value:
            expected_escalations += 1
        else:
            high_value_policy_escalations += 1

    return {
        "low_confidence_escalations": low_confidence_escalations,
        "expected_escalations": expected_escalations,
        "high_value_policy_escalations": high_value_policy_escalations,
        "total_escalations": (
            low_confidence_escalations
            + expected_escalations
            + high_value_policy_escalations
        ),
    }


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

    escalation_breakdown = _compute_escalation_breakdown(agent_decisions)

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
        "escalation_breakdown": escalation_breakdown,
        # kept for backward compatibility with the dashboard/any code still
        # reading the old combined field -- equals high_value_policy_escalations,
        # i.e. exactly what the old single-bucket definition counted
        "false_escalation_count": escalation_breakdown["high_value_policy_escalations"],
        "gate1_low_confidence_overrides": gate1_overrides,
        "fallback_actions_used": fallback_used,
        "fallback_actions_executed": fallback_executed,
        "fallback_actions_recovered_money": fallback_recovered_money,
    }