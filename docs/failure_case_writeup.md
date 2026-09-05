# Failure Case Writeup

Real decisions pulled from the audit ledger of `batch_001` (300-event synthetic batch, seed 1).
This is not a synthetic illustration — every value below is copied from the actual audit log.

**Note:** this writeup should be regenerated after any change to the policy, gate logic, or
compliance rules — the specific decision IDs and amounts here are tied to `batch_001` as it
stood on 2026-09-05. Re-run `run_batch.py` and swap in fresh examples once the code changes.

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

**What happened:** the diagnostician classified this as `soft_decline`, but at only 0.40
confidence — well below the threshold the policy needs to trust a cheap, automated retry.
Gate 1 stepped in and overrode the policy's default (`retry_in_4h`) to the safer, human-backed
`human_escalation`, at a real cost of ₹50. In this instance the escalation didn't recover the
payment. This is not a bug — it's the override behaving exactly as designed: when the system
isn't confident in its own diagnosis, it pays a small cost for a safer path rather than betting
on an automated action it isn't sure will work. The cost of being wrong here is bounded (₹50),
which is the point of the gate.

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
was blocked.

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
isn't a fig leaf over lost revenue: it's a real, working second attempt that recovers money in
some fraction of cases the primary action never got a chance to try.

---

## Summary

Across these three cases, the compliance layer never let an unsafe or non-compliant action
through, and never left a customer un-attempted when a safe fallback existed. Two of the three
outcomes were misses — which is expected and honestly reported, not hidden. The value being
demonstrated here is not "the system always recovers the payment," it's "the system never skips
its safety checks to try, and degrades gracefully (fallback, bounded-cost escalation) when its
first choice is blocked or its diagnosis is uncertain."
