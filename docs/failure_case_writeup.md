# Failure Case Writeup

Real decisions pulled from the audit ledger of `batch_001` (300-event synthetic batch, seed 1),
cross-verified against both the batch script output and the live `/metrics/{batch_id}` API
response on 2026-09-06.

**Note:** this writeup should be regenerated after any change to the policy, gate logic, or
compliance rules — the specific decision IDs and amounts here are tied to `batch_001` as it
stood on this date. Re-run `run_batch.py` and swap in fresh examples once the code changes.

---

## Escalation breakdown (batch_001, 300 events)

The `false_escalation_count` metric from earlier runs conflated three genuinely different
situations into one number. Splitting it (see `backend/app/metrics/report.py`) gives:

| Bucket | Count | What it means |
|---|---|---|
| `low_confidence_escalations` | 9 | Gate 1 overrode a low-confidence diagnosis into `human_escalation`. A hedge, not a mistake. |
| `expected_escalations` | 73 | `willful_non_payment` cases, where escalation is the designed default action for that category. |
| `high_value_policy_escalations` | 29 | The policy itself chose `human_escalation` (no override) for a non-willful category — typically a high-value transaction where the expected-value math favored a human follow-up over an automated retry. |
| **Total** | **111** | Sum of all three. |

The old single `false_escalation_count` field silently equaled just the `high_value_policy_escalations`
bucket (29) — this writeup exists partly to make that mapping explicit and auditable, since it wasn't
obvious from the field name alone. `low_confidence_escalations` (9) exactly matches
`gate1_low_confidence_overrides` (9) from the same run, confirming the split logic is internally
consistent: every Gate-1-driven escalation is, by definition, also counted as a Gate-1 override.

---

## Case 1 — Gate 1 low-confidence override (miss)

**Decision ID:** `DEC-002915` | **Customer:** `cust_141`

| Field | Value |
|---|---|
| Diagnosed category | `soft_decline` |
| Diagnosis confidence | 0.40 |
| Original policy action | `retry_in_4h` |
| Gate 1 override | **Yes** |
| Chosen action (post-override) | `human_escalation` |
| Gate 2 | Passed |
| Executed | Yes |
| Outcome | Not recovered |
| Action cost | ₹50.00 |
| Escalation bucket | `low_confidence_escalations` |

**What happened:** the diagnostician classified this as `soft_decline`, but at only 0.40
confidence — well below the threshold the policy needs to trust a cheap, automated retry.
Gate 1 stepped in and overrode the policy's default (`retry_in_4h`) to the safer, human-backed
`human_escalation`, at a real cost of ₹50. In this instance the escalation didn't recover the
payment. This is not a bug — it's the override behaving exactly as designed: when the system
isn't confident in its own diagnosis, it pays a small, bounded cost for a safer path rather than
betting on an automated action it isn't sure will work. This case is one of 9 in the
`low_confidence_escalations` bucket for this batch — none of these are "false" escalations in
any meaningful sense; they're the system correctly hedging on uncertainty.

---

## Case 2 — Gate 2 compliance rejection → fallback (miss)

**Decision ID:** `DEC-002863` | **Customer:** `cust_138`

| Field | Value |
|---|---|
| Diagnosed category | `genuine_abandonment` |
| Diagnosis confidence | 0.80 |
| Attempted action | `alt_payment_link` |
| Gate 2 result | **Rejected** — `cooldown_active (elapsed 0:19:26 < required 1 day, 0:00:00)` |
| Fallback action | `retry_in_24h` |
| Fallback Gate 2 | Passed |
| Executed | Yes (fallback) |
| Outcome | Not recovered |
| Action cost | ₹0.00 |

**What happened:** the policy's first choice, `alt_payment_link`, was correctly diagnosed at
high confidence (0.80) — the problem wasn't the diagnosis, it was compliance. This customer had
been contacted only 19 minutes earlier, well inside the required 1-day cooldown window. Gate 2
rejected the primary action outright rather than letting it execute anyway. The system then
fell back to `retry_in_24h`, a pre-approved safe default that passed compliance and executed.
The fallback didn't recover the payment this time, but the important part is what *didn't*
happen: the customer wasn't contacted twice in 20 minutes just because the first-choice action
was blocked. This case is one of 134 `cooldown_active` rejections in the batch — all 134 were
successfully caught by the fallback path (`fallback_actions_used: 134`,
`fallback_actions_executed: 134`), though only 18 of those 134 fallbacks (`fallback_actions_recovered_money: 18`)
went on to recover money.

---

## Case 3 — Gate 2 rejection → fallback (recovery)

**Decision ID:** `DEC-002919` | **Customer:** `cust_200`

| Field | Value |
|---|---|
| Diagnosed category | `genuine_abandonment` |
| Diagnosis confidence | 0.80 |
| Attempted action | `alt_payment_link` |
| Gate 2 result | **Rejected** — `cooldown_active (elapsed 0:19:24 < required 1 day, 0:00:00)` |
| Fallback action | `retry_in_24h` |
| Fallback Gate 2 | Passed |
| Executed | Yes (fallback) |
| Outcome | **Recovered** |
| Amount recovered | ₹5,371.53 |
| Action cost | ₹0.00 |

**What happened:** same rejection pattern as Case 2 — same category, same cooldown reason, same
fallback action chosen. This time the fallback recovered the payment at zero action cost. The
side-by-side of Case 2 and Case 3 is the clearest evidence in this batch that the fallback path
isn't a fig leaf over lost revenue: it's a real, working second attempt that recovered money in
18 of 134 cases (13.4%) where the primary action never got a chance to try.

---

## Summary

Across 300 events, 134 primary actions were rejected by Gate 2 for the same reason
(`cooldown_active`), and all 134 fell back gracefully rather than being dropped — 18 of those
fallbacks went on to recover money that the primary action, blocked on compliance grounds,
never had the chance to attempt. Separately, of 111 total `human_escalation` decisions, only 29
represent the policy independently choosing escalation over an automated action for a
non-willful category; the remaining 82 are either the designed default for
`willful_non_payment` (73) or a Gate 1 confidence hedge (9) — neither of which should be read as
the system "wrongly" escalating.

The value being demonstrated here is not "the system always recovers the payment" — two of the
three individual cases above were misses, reported honestly rather than cherry-picked. It's that
the compliance layer never lets an unsafe or non-compliant action through, never leaves a
customer un-attempted when a safe fallback exists, and that what looks like a single blunt
"false escalation" number actually decomposes into three behaviors with very different — and
mostly defensible — reasons behind them.