import random
from collections import defaultdict

from backend.app.config import CANDIDATE_ACTIONS
from backend.app.policy.expected_value import expected_net_value


class BetaBernoulliBanditPolicy:
    """Thompson sampling per (category:segment, action) bucket."""

    def __init__(self):
        self._alpha_beta = defaultdict(lambda: [1.0, 1.0])

    def _key(self, category, segment, action):
        return (f"{category.value}:{segment}", action)

    def select_action(self, category, context, amount_inr):
        segment = (context or {}).get("segment", "default")
        candidates = CANDIDATE_ACTIONS[category]
        best_action = None
        best_value = float("-inf")
        best_belief = None
        for action in candidates:
            alpha, beta = self._alpha_beta[self._key(category, segment, action)]
            sampled_p = random.betavariate(alpha, beta)
            value = expected_net_value(sampled_p, amount_inr, action)
            if value > best_value:
                best_value = value
                best_action = action
                best_belief = sampled_p
        return best_action, best_belief

    def update(self, category, context, action, recovered: bool):
        segment = (context or {}).get("segment", "default")
        key = self._key(category, segment, action)
        alpha, beta = self._alpha_beta[key]
        if recovered:
            alpha += 1
        else:
            beta += 1
        self._alpha_beta[key] = [alpha, beta]


bandit_policy = BetaBernoulliBanditPolicy()