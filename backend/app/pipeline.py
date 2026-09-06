import random

from sqlalchemy.orm import Session

from backend.app.config import settings, Action, FALLBACK_ACTION, ACTION_COST_INR
from backend.app.detector.ingest import ingest_events
from backend.app.diagnostician.rules import diagnose_rule_based
from backend.app.diagnostician.llm_reasoner import diagnose_with_llm
from backend.app.policy.baseline_policy import select_action_rule_based
from backend.app.policy.bandit_policy import bandit_policy
from backend.app.compliance import gate
from backend.app.executor.simulate import simulate
from backend.app.baseline.naive_retry import baseline_action_for, BASELINE_CATEGORY
from backend.app.auditor.ledger import record_decision


def _select_policy_action(category, event, amount_inr):
    if settings.policy_mode == "bandit":
        action, confidence = bandit_policy.select_action(category, event.context, amount_inr)
    else:
        action, confidence = select_action_rule_based(category, amount_inr)
    return action, confidence


def process_event_agent(db: Session, event, outcome_rng: random.Random = None) -> dict:
    category, confidence, source = diagnose_rule_based(event)
    if settings.use_llm_diagnosis and confidence < settings.diagnosis_confidence_threshold:
        category, confidence, source = diagnose_with_llm(event, category, confidence)

    action, policy_confidence = _select_policy_action(category, event, event.amount_inr)

    gate1_override = False
    original_policy_action = None
    if confidence < settings.diagnosis_confidence_threshold and action != Action.HUMAN_ESCALATION:
        gate1_override = True
        original_policy_action = action.value
        action = Action.HUMAN_ESCALATION

    passed, reasons = gate.evaluate(db, event, action)

    fallback_action = None
    fallback_passed = None
    executed = False
    outcome = None
    amount_recovered = 0.0
    final_action = action

    if passed:
        executed = True
        outcome, amount_recovered = simulate(category, action, event.amount_inr, rng=outcome_rng)
    else:
        fb = FALLBACK_ACTION.get(action)
        if fb is not None:
            fallback_action = fb.value
            fb_passed, fb_reasons = gate.evaluate(db, event, fb)
            fallback_passed = fb_passed
            if fb_passed:
                final_action = fb
                executed = True
                outcome, amount_recovered = simulate(category, fb, event.amount_inr, rng=outcome_rng)

    if settings.policy_mode == "bandit" and not gate1_override:
        if passed:
            bandit_policy.update(category, event.context, action, outcome == "recovered")
        else:
            bandit_policy.update(category, event.context, action, False)
            if executed:
                bandit_policy.update(category, event.context, final_action, outcome == "recovered")

    decision = record_decision(
        db,
        batch_id=event.batch_id,
        event_id=event.id,
        customer_id=event.customer_id,
        is_baseline=False,
        diagnosed_category=category.value,
        diagnosis_confidence=confidence,
        diagnosis_source=source,
        chosen_action=action.value,
        policy_confidence=policy_confidence,
        gate1_low_confidence_override=gate1_override,
        original_policy_action=original_policy_action,
        compliance_passed=passed,
        compliance_rejection_reasons=reasons,
        fallback_action=fallback_action,
        fallback_compliance_passed=fallback_passed,
        executed=executed,
        outcome=outcome,
        amount_recovered_inr=amount_recovered,
        action_cost_inr=ACTION_COST_INR[final_action],
    )
    return decision


def process_event_baseline(db: Session, event, outcome_rng: random.Random = None) -> dict:
    action = baseline_action_for(event)
    executed = False
    outcome = None
    amount_recovered = 0.0
    action_cost = 0.0

    if action is not None:
        executed = True
        outcome, amount_recovered = simulate(BASELINE_CATEGORY, action, event.amount_inr, rng=outcome_rng)
        action_cost = ACTION_COST_INR[action]

    decision = record_decision(
        db,
        batch_id=event.batch_id,
        event_id=event.id,
        customer_id=event.customer_id,
        is_baseline=True,
        diagnosed_category=None,
        diagnosis_confidence=None,
        diagnosis_source=None,
        chosen_action=action.value if action else None,
        policy_confidence=None,
        gate1_low_confidence_override=False,
        original_policy_action=None,
        compliance_passed=True,
        compliance_rejection_reasons=[],
        fallback_action=None,
        fallback_compliance_passed=None,
        executed=executed,
        outcome=outcome,
        amount_recovered_inr=amount_recovered,
        action_cost_inr=action_cost,
    )
    return decision


def run_batch(db: Session, batch_id: str, raw_events: list[dict], outcome_seed: int = None) -> dict:
    events, inserted_count, skipped_count = ingest_events(db, batch_id, raw_events)

    outcome_rng = random.Random(outcome_seed) if outcome_seed is not None else None

    for event in events:
        process_event_agent(db, event, outcome_rng=outcome_rng)
        process_event_baseline(db, event, outcome_rng=outcome_rng)

    from backend.app.metrics.report import build_metrics_report
    report = build_metrics_report(db, batch_id)
    report["events_inserted"] = inserted_count
    report["events_skipped"] = skipped_count
    return report
