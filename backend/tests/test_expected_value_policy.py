from backend.app.config import FailureCategory, Action
from backend.app.policy.baseline_policy import select_action_rule_based


def test_amount_changes_which_action_wins_hard_decline():
    low_amount = 100
    action, conf = select_action_rule_based(FailureCategory.HARD_DECLINE, low_amount)
    assert action == Action.ALT_PAYMENT_LINK
    assert conf == 1.0

    high_amount = 100000
    action, conf = select_action_rule_based(FailureCategory.HARD_DECLINE, high_amount)
    assert action == Action.HUMAN_ESCALATION


def test_soft_decline_picks_best_expected_value():
    action, _ = select_action_rule_based(FailureCategory.SOFT_DECLINE, 1000)
    assert action == Action.RETRY_IN_4H


def test_gateway_error_picks_retry_now():
    action, _ = select_action_rule_based(FailureCategory.GATEWAY_ERROR, 1000)
    assert action == Action.RETRY_NOW