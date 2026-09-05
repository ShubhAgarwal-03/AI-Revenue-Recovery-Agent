from backend.app.config import CANDIDATE_ACTIONS
from backend.app.executor.simulate import RESPONSE_RATES
from backend.app.policy.expected_value import expected_net_value


def select_action_rule_based(category, amount_inr):
    candidates = CANDIDATE_ACTIONS[category]
    best_action = None
    best_value = float("-inf")
    for action in candidates:
        p = RESPONSE_RATES.get((category, action), 0.10)
        value = expected_net_value(p, amount_inr, action)
        if value > best_value:
            best_value = value
            best_action = action
    return best_action, 1.0