from backend.app.config import ACTION_COST_INR


def expected_net_value(p_recover: float, amount_inr: float, action) -> float:
    return p_recover * amount_inr - ACTION_COST_INR[action]