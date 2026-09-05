from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class FailureCategory(str, Enum):
    SOFT_DECLINE = "soft_decline"
    HARD_DECLINE = "hard_decline"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    GATEWAY_ERROR = "gateway_error"
    GENUINE_ABANDONMENT = "genuine_abandonment"
    MANDATE_EXPIRY = "mandate_expiry"
    WILLFUL_NON_PAYMENT = "willful_non_payment"


class Action(str, Enum):
    RETRY_NOW = "retry_now"
    RETRY_IN_4H = "retry_in_4h"
    RETRY_IN_24H = "retry_in_24h"
    SMS_NUDGE = "sms_nudge"
    WHATSAPP_NUDGE = "whatsapp_nudge"
    VOICE_REMINDER_HINGLISH = "voice_reminder_hinglish"
    ALT_PAYMENT_LINK = "alt_payment_link"
    HUMAN_ESCALATION = "human_escalation"
    WRITE_OFF = "write_off"


ACTION_COST_INR = {
    Action.RETRY_NOW: 0,
    Action.RETRY_IN_4H: 0,
    Action.RETRY_IN_24H: 0,
    Action.SMS_NUDGE: 0.5,
    Action.WHATSAPP_NUDGE: 1,
    Action.VOICE_REMINDER_HINGLISH: 5,
    Action.ALT_PAYMENT_LINK: 0.5,
    Action.HUMAN_ESCALATION: 50,
    Action.WRITE_OFF: 0,
}

CANDIDATE_ACTIONS = {
    FailureCategory.SOFT_DECLINE: [Action.RETRY_NOW, Action.RETRY_IN_4H, Action.SMS_NUDGE],
    FailureCategory.HARD_DECLINE: [Action.ALT_PAYMENT_LINK, Action.HUMAN_ESCALATION],
    FailureCategory.INSUFFICIENT_FUNDS: [Action.RETRY_IN_24H, Action.SMS_NUDGE],
    FailureCategory.GATEWAY_ERROR: [Action.RETRY_NOW, Action.RETRY_IN_4H],
    FailureCategory.GENUINE_ABANDONMENT: [Action.SMS_NUDGE, Action.WHATSAPP_NUDGE, Action.ALT_PAYMENT_LINK],
    FailureCategory.MANDATE_EXPIRY: [Action.SMS_NUDGE, Action.ALT_PAYMENT_LINK, Action.WHATSAPP_NUDGE],
    FailureCategory.WILLFUL_NON_PAYMENT: [
        Action.WHATSAPP_NUDGE, Action.VOICE_REMINDER_HINGLISH, Action.HUMAN_ESCALATION, Action.WRITE_OFF,
    ],
}

CONTACT_ACTIONS = {
    Action.SMS_NUDGE, Action.WHATSAPP_NUDGE, Action.VOICE_REMINDER_HINGLISH, Action.ALT_PAYMENT_LINK,
}

FALLBACK_ACTION = {
    Action.SMS_NUDGE: Action.RETRY_IN_24H,
    Action.WHATSAPP_NUDGE: Action.RETRY_IN_24H,
    Action.VOICE_REMINDER_HINGLISH: Action.RETRY_IN_24H,
    Action.ALT_PAYMENT_LINK: Action.RETRY_IN_24H,
    Action.HUMAN_ESCALATION: Action.WRITE_OFF,
}


class Settings(BaseSettings):
    database_url: str = "sqlite:///./revenue_recovery.db"
    policy_mode: str = "rule_based"

    use_llm_diagnosis: bool = False
    anthropic_api_key: str = ""

    diagnosis_confidence_threshold: float = 0.5

    max_contacts_per_customer_per_window: int = 3
    contact_cooldown_hours: int = 24
    contact_hours_start: int = 9
    contact_hours_end: int = 20
    spend_ceiling_inr: float = 500

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()