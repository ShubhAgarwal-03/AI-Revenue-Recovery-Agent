# AI Revenue Recovery Engine

**Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**

A recovery engine that doesn't just retry failed payments — it diagnoses *why* revenue is at risk, picks an intervention per failure category, runs every action through a two-gate compliance check before it's allowed to execute, and proves its lift against a fixed baseline. Every decision is logged immutably for audit.

---

## What it does

1. **Detect** — ingests payment/checkout/subscription/receivables failure events.
2. **Diagnose** — classifies each failure into a root-cause category (soft decline, hard decline, insufficient funds, gateway error, genuine abandonment, mandate expiry, willful non-payment) with a confidence score.
3. **Decide** — a rule-based policy picks the best action per category (retry now, retry in 4h/24h, alternate payment link, human escalation), weighing expected recovery against action cost.
4. **Gate** — every action passes through two compliance checks before it's allowed to run:
   - **Gate 1**: low-confidence diagnoses are overridden toward a safer default action.
   - **Gate 2**: cooldown, contact-frequency, and other compliance rules can reject an action outright; a rejected action falls back to a pre-approved safe default (e.g. `retry_in_24h`) instead of doing nothing.
5. **Execute** — runs the (possibly fallback) action and records the outcome.
6. **Compare** — every event also runs a fixed baseline action in parallel, so recovery lift is measured against a real counterfactual, not an assumption.
7. **Audit** — every decision (diagnosis, chosen action, gate results, fallback, outcome, amount recovered) is written to an immutable ledger.

## Architecture

```
Event → Detector → Diagnostician → Policy → Gate 1 (confidence)
                                              │
                                     Gate 2 (compliance)
                                        │           │
                                     passed       rejected → Fallback action → Gate 2 (again)
                                        │                          │
                                        └──────────┬───────────────┘
                                                   Executor
                                                     │
                                              Outcome + Audit log
                                                     │
                                          (parallel: Baseline action on same event)
```

Core pipeline components live under `backend/app/` — detector, diagnostician, policy, compliance gate, executor, baseline runner, auditor, metrics. See `AI_Revenue_Recovery_PRD.md` and the architecture doc in `docs/` for the full spec.

## Dashboard

A single dependency-free HTML file at `dashboard/index.html` (Chart.js loaded from CDN, no build step) that visualizes a batch run:

- KPI row — recovery rate, lift vs. baseline, compliance rejections, fallback usage
- Recovery funnel — detected → Gate 1 → Gate 2 → executed → recovered
- Root-cause breakdown (donut) and compliance-rejection reasons (bar)
- Exception list — cases where nothing was ever successfully executed
- Cross-batch trend chart — recovery rate and lift across all runs
- Filterable, sortable audit ledger table

It reads live from the API — no backend changes needed, no mock data.

## Setup

```bash
# from repo root
python -m venv venv
venv\Scripts\activate        # or `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

## Running a batch

```bash
python data/synthetic_generator.py --n 300 --out data/events/batch_001.json --seed 1
python backend/scripts/run_batch.py --batch data/events/batch_001.json --batch-id batch_001
```

This prints a metrics summary (recovery rate, lift, compliance rejections, fallback stats) and writes decisions to the audit store.

## Running the dashboard

```bash
uvicorn backend.app.main:app --reload
```

Open `http://127.0.0.1:8000/dashboard` and pick a batch from the dropdown.

## Running the bandit experiment

```bash
python backend/scripts/run_bandit_experiment.py
```

Runs 20 rounds of 400 events each (8,000 events total) against the contextual bandit policy, with outcome simulation seeded per round for reproducibility of the recovery draw. Reports the real recovery-rate trend — see `docs/known_issues.md` for the honestly-reported result: recovery rate hovers in a ~0.19–0.27 band with no reliable directional trend, and a linear regression across all 20 points comes out effectively flat.

## Tests

```bash
pytest backend/tests/ -v
```
20/20 passing.

## Repo layout

```
backend/
  app/           # detector, diagnostician, policy, gates, executor, baseline, auditor, metrics, API
  scripts/       # run_batch.py, run_bandit_experiment.py
  tests/         # pytest suite
data/
  synthetic_generator.py
  events/        # generated batches
dashboard/
  index.html     # standalone dashboard, no build step
docs/
  AI_Revenue_Recovery_PRD.md
  known_issues.md
  failure_case_writeup.md
```

## Known limitations

This project intentionally documents its own failure modes rather than hiding them — see `docs/known_issues.md` and `docs/failure_case_writeup.md` for details, including:

- The contextual bandit's recovery-rate trend across 20 rounds is flat/inconclusive at this event volume, not net-negative — a naive "first 3 rounds vs last 3 rounds" comparison is noise-sensitive enough that three independent clean runs of the same seeds produced three different verdicts (net-negative, net-positive, net-positive). A regression slope across all 20 points (≈ −0.0004/batch) is the number we trust.
- The bandit's action-selection randomness (Thompson sampling) isn't currently seeded — only outcome simulation is — so full run-to-run reproducibility in bandit mode isn't achieved yet.
- `false_escalation_count` is now split into `low_confidence_escalations`, `expected_escalations`, `high_value_policy_escalations`, and `total_escalations` — the old field conflated Gate 1 overrides with deliberate, correct high-value escalations. Old field kept for backward compatibility.

## License / attribution

Built for Razorpay AI Buildathon 2026, Track 03.