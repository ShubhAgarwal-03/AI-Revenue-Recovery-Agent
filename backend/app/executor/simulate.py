import random

from backend.app.config import FailureCategory, Action

RESPONSE_RATES = {
    (FailureCategory.SOFT_DECLINE, Action.RETRY_NOW): 0.35,
    (FailureCategory.SOFT_DECLINE, Action.RETRY_IN_4H): 0.55,
    (FailureCategory.SOFT_DECLINE, Action.SMS_NUDGE): 0.20,

    (FailureCategory.HARD_DECLINE, Action.ALT_PAYMENT_LINK): 0.30,
    (FailureCategory.HARD_DECLINE, Action.HUMAN_ESCALATION): 0.45,

    (FailureCategory.INSUFFICIENT_FUNDS, Action.RETRY_IN_24H): 0.45,
    (FailureCategory.INSUFFICIENT_FUNDS, Action.SMS_NUDGE): 0.25,

    (FailureCategory.GATEWAY_ERROR, Action.RETRY_NOW): 0.70,
    (FailureCategory.GATEWAY_ERROR, Action.RETRY_IN_4H): 0.60,

    (FailureCategory.GENUINE_ABANDONMENT, Action.SMS_NUDGE): 0.15,
    (FailureCategory.GENUINE_ABANDONMENT, Action.WHATSAPP_NUDGE): 0.25,
    (FailureCategory.GENUINE_ABANDONMENT, Action.ALT_PAYMENT_LINK): 0.28,

    (FailureCategory.MANDATE_EXPIRY, Action.SMS_NUDGE): 0.40,
    (FailureCategory.MANDATE_EXPIRY, Action.ALT_PAYMENT_LINK): 0.50,
    (FailureCategory.MANDATE_EXPIRY, Action.WHATSAPP_NUDGE): 0.45,

    (FailureCategory.WILLFUL_NON_PAYMENT, Action.WHATSAPP_NUDGE): 0.08,
    (FailureCategory.WILLFUL_NON_PAYMENT, Action.VOICE_REMINDER_HINGLISH): 0.12,
    (FailureCategory.WILLFUL_NON_PAYMENT, Action.HUMAN_ESCALATION): 0.20,
}

DEFAULT_RATE = 0.10


def simulate(category, action, amount_inr):
    if action == Action.WRITE_OFF:
        return "not_recovered", 0.0
    rate = RESPONSE_RATES.get((category, action), DEFAULT_RATE)
    if random.random() < rate:
        return "recovered", amount_inr
    return "not_recovered", 0.0
