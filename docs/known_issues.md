# Known Issues

Honest accounting of what's unresolved, based on real runs, not assumed to be clean.

---

## 1. Bandit policy's action selection is not seeded — full reproducibility not yet achieved

`backend/app/executor/simulate.py` accepts an `outcome_rng` that's seeded per bandit
round via `outcome_seed`, so the *recovery outcome* draw is reproducible. However,
`bandit_policy.select_action()`'s Thompson sampling (drawing from Beta distributions
per context-bucket × action) uses its own unseeded random source, so the bandit can
choose a *different action* for the same event on different runs even with the same
`outcome_seed`.

**Evidence:** three independent, fully clean (DB reset between each) runs of the
20-round × 400-event bandit experiment, using the identical seed sequence 1–20,
produced three different recovery-rate sequences and three different first-3/last-3
trend verdicts:

| Run | Mean first 3 | Mean last 3 | Delta | Verdict |
|---|---|---|---|---|
| Original | 0.2392 | 0.2150 | −0.0242 | NET-NEGATIVE |
| Clean run 1 | 0.2000 | 0.2167 | +0.0167 | NET-POSITIVE |
| Clean run 2 | 0.1967 | 0.2183 | +0.0217 | NET-POSITIVE |

**Fix (not done, time-permitting):** thread an optional `rng` parameter through
`bandit_policy.select_action()` the same way `simulate()` already does, seeded from
the same per-round seed.

## 2. The first-3/last-3 trend metric is unreliable — use regression slope instead

The table above is itself the proof: the same 20 seeds gave three different directional
verdicts depending on random variation in policy selection alone. A linear regression
across all 20 points of the original run gives a slope of **≈ −0.0004 per batch**
(cumulative drift of about −0.007 over 20 rounds) — i.e., **effectively flat**, not a
meaningful negative trend. This is the number we report, not the window-dependent
first-3/last-3 comparison.

**Root-cause hypothesis (not fully verified):** `data/synthetic_generator.py` draws
each event from failure categories uniformly at random. Category response rates vary
hugely — `willful_non_payment` actions cap at 8–20%, `gateway_error` actions hit
60–70% — so which category mix a given seed happens to draw likely dominates
batch-to-batch recovery-rate variance, independent of anything the bandit is or isn't
learning. Whether bucket sample sizes (category × segment × action) are still too
sparse at n=400/round to let the bandit converge within 20 rounds has not been
checked directly.

## 3. Escalation counts were previously conflated — now split, but not all "escalations" are failures

`false_escalation_count` used to lump together every `human_escalation` decision that
wasn't a confidence override. On `batch_001` (n=300 events), the real split is:

| Field | Count |
|---|---|
| `low_confidence_escalations` (Gate 1 override) | 9 |
| `expected_escalations` (policy chose escalation directly) | 73 |
| `high_value_policy_escalations` (expected-value math favors escalation at high amounts) | 29 |
| `total_escalations` | 111 |

The `high_value_policy_escalations` bucket is **not** a mistake — for high-value
`hard_decline` cases, the expected-value calculation genuinely favors human escalation
over a payment link. The old single `false_escalation_count` field made the policy look
worse than it is by not distinguishing "escalated because confidence was low" from
"escalated because the math says escalation is the right call at this amount." Old
field preserved for backward compatibility.

## 4. Compliance rejections on a single batch are dominated by `cooldown_active`

On `batch_001` (300 events), all 134 compliance rejections were `cooldown_active`.
This is a batch-generation artifact, not an overly strict gate: 300 events over a
smaller synthetic customer pool naturally produces repeat `customer_id`s within one
batch run, which trips the cooldown window. Of the 134 rejected actions, all 134 fell
back successfully and executed (100% graceful degradation), but only 18 of those
fallbacks actually recovered money — worth distinguishing "the fallback fired" from
"the fallback worked" when reporting this number.

## 5. Repo cleanup

`backend/scripts/run_bandit_experience.py` (typo'd duplicate of
`run_bandit_experiment.py`, with a slightly different return signature) should be
deleted to avoid confusing anyone browsing the repo.

## 6. Not implemented: multi-channel cost/success tradeoffs

The PRD's stretch goal of treating SMS / WhatsApp / voice as distinct channels with
different cost and success-rate tradeoffs (rather than one fixed action = one fixed
cost/rate) was not built. Each contact action currently has a single fixed cost and
response rate baked into `simulate.py`'s `RESPONSE_RATES` table.