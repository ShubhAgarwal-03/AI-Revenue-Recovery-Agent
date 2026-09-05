from backend.app.config import FailureCategory

DECLINE_CODE_MAP = {
    "insufficient_funds": FailureCategory.INSUFFICIENT_FUNDS,
    "do_not_honor": FailureCategory.HARD_DECLINE,
    "expired_card": FailureCategory.HARD_DECLINE,
    "invalid_cvv": FailureCategory.SOFT_DECLINE,
    "issuer_timeout": FailureCategory.SOFT_DECLINE,
    "risk_block": FailureCategory.HARD_DECLINE,
}


def diagnose_rule_based(event) -> tuple[FailureCategory, float, str]:
    context = event.context or {}

    if event.event_type == "checkout_abandonment":
        return FailureCategory.GENUINE_ABANDONMENT, 0.8, "rule_based"

    if event.event_type == "mandate_failure":
        return FailureCategory.MANDATE_EXPIRY, 0.9, "rule_based"

    if event.event_type == "overdue_invoice":
        days_overdue = context.get("days_overdue", 0)
        past_rate = context.get("past_on_time_payment_rate", 1.0)
        if days_overdue > 60 and past_rate < 0.3:
            return FailureCategory.WILLFUL_NON_PAYMENT, 0.7, "rule_based"
        return FailureCategory.WILLFUL_NON_PAYMENT, 0.4, "rule_based"

    if event.event_type == "payment_failure":
        if event.gateway_error:
            return FailureCategory.GATEWAY_ERROR, 0.85, "rule_based"
        if event.decline_code in DECLINE_CODE_MAP:
            return DECLINE_CODE_MAP[event.decline_code], 0.85, "rule_based"
        return FailureCategory.SOFT_DECLINE, 0.4, "rule_based"

    return FailureCategory.SOFT_DECLINE, 0.2, "rule_based"