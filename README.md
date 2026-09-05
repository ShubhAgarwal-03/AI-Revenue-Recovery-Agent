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

Runs 10 rounds of the contextual bandit policy and reports the real recovery-rate trend — see `docs/known_issues.md` for the current (honestly reported) result and open questions around sample size.

## Tests

```bash
pytest backend/tests/ -v
```

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

- The contextual bandit shows a net-negative recovery-rate trend over 10 rounds, likely due to sparse per-bucket samples (category × segment × action) — see known issues for the follow-up experiment.
- `false_escalation_count` currently conflates low-confidence overrides with deliberate high-value escalations; a split metric is proposed but not yet implemented.

## License / attribution

Built for Razorpay AI Buildathon 2026, Track 03.
