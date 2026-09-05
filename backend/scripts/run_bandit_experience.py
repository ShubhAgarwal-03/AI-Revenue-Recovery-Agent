"""
Runs 10 sequential batches of 100 events each through the bandit policy,
in-process, so the bandit_policy singleton's learned beliefs persist across
batches (not relying on server restarts). Prints each batch's recovery_rate
and reports whether the trend (mean of last 3 vs mean of first 3) is
net-positive, net-negative, or flat -- printed honestly either way.
"""
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.config import settings
settings.policy_mode = "bandit"  # must be set before pipeline module reads it per-call

from backend.app.db import init_db, SessionLocal, engine
from backend.app.pipeline import run_batch
from data.synthetic_generator import generate


def main():
    init_db(engine)
    db = SessionLocal()
    rates = []
    try:
        for i, seed in enumerate(range(1, 11), start=1):
            events = generate(100, seed=seed)
            batch_id = f"bandit_experiment_batch_{i}"
            report = run_batch(db, batch_id, events)
            rates.append(report["recovery_rate"])
            print(f"batch {i} (seed={seed}): recovery_rate={report['recovery_rate']:.4f}")
    finally:
        db.close()

    first_three = sum(rates[:3]) / 3
    last_three = sum(rates[-3:]) / 3
    delta = last_three - first_three

    print()
    print("All 10 recovery rates:", [round(r, 4) for r in rates])
    print(f"Mean of first 3 batches: {first_three:.4f}")
    print(f"Mean of last 3 batches:  {last_three:.4f}")
    if delta > 0.01:
        verdict = "NET-POSITIVE"
    elif delta < -0.01:
        verdict = "NET-NEGATIVE"
    else:
        verdict = "FLAT (no meaningful trend)"
    print(f"Trend: {verdict} (delta={delta:+.4f})")

    return rates, first_three, last_three, verdict


if __name__ == "__main__":
    main()