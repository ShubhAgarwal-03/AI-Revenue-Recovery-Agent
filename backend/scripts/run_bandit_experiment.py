import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.config import settings
settings.policy_mode = "bandit"

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
            rate = report["recovery_rate"]
            rates.append(rate)
            print(f"batch {i} (seed={seed}): recovery_rate={rate:.4f}")
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


if __name__ == "__main__":
    main()
