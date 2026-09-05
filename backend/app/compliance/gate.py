from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from backend.app.config import settings, ACTION_COST_INR, CONTACT_ACTIONS
from backend.app.models import Decision


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def check_contact_limit(db: Session, customer_id: str) -> str | None:
    count = (
        db.query(Decision)
        .filter(
            Decision.customer_id == customer_id,
            Decision.compliance_passed == True,  # noqa: E712
            Decision.chosen_action.in_([a.value for a in CONTACT_ACTIONS]),
        )
        .count()
    )
    if count >= settings.max_contacts_per_customer_per_window:
        return f"contact_limit_exceeded ({count} >= {settings.max_contacts_per_customer_per_window})"
    return None


def get_last_contact_at(db: Session, customer_id: str):
    last = (
        db.query(Decision)
        .filter(
            Decision.customer_id == customer_id,
            Decision.executed == True,  # noqa: E712
            Decision.chosen_action.in_([a.value for a in CONTACT_ACTIONS]),
        )
        .order_by(Decision.created_at.desc())
        .first()
    )
    return last.created_at if last else None


def check_cooldown(db: Session, customer_id: str, now: datetime) -> str | None:
    last_contact_at = get_last_contact_at(db, customer_id)
    if last_contact_at is None:
        return None
    last_contact_at = _as_utc(last_contact_at)
    now = _as_utc(now)
    elapsed = now - last_contact_at
    cooldown = timedelta(hours=settings.contact_cooldown_hours)
    if elapsed < cooldown:
        return f"cooldown_active (elapsed {elapsed} < required {cooldown})"
    return None


def check_opt_out(event) -> str | None:
    if (event.context or {}).get("opted_out"):
        return "customer_opted_out"
    return None


def check_contact_hours(now: datetime) -> str | None:
    if not (settings.contact_hours_start <= now.hour < settings.contact_hours_end):
        return f"outside_contact_hours (hour={now.hour})"
    return None


def check_spend_ceiling(action) -> str | None:
    cost = ACTION_COST_INR[action]
    if cost > settings.spend_ceiling_inr:
        return f"spend_ceiling_exceeded ({cost} > {settings.spend_ceiling_inr})"
    return None


def evaluate(db: Session, event, action, now: datetime | None = None) -> tuple[bool, list[str]]:
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []

    if action in CONTACT_ACTIONS:
        for check, args in (
            (check_contact_limit, (db, event.customer_id)),
            (check_cooldown, (db, event.customer_id, now)),
            (check_opt_out, (event,)),
            (check_contact_hours, (now,)),
        ):
            reason = check(*args)
            if reason:
                reasons.append(reason)

    reason = check_spend_ceiling(action)
    if reason:
        reasons.append(reason)

    return len(reasons) == 0, reasons