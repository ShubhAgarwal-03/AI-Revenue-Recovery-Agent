from backend.app.config import Action, FailureCategory


def baseline_action_for(event):
    if event.event_type in ("payment_failure", "mandate_failure"):
        return Action.RETRY_IN_24H
    return None


BASELINE_CATEGORY = FailureCategory.SOFT_DECLINE
