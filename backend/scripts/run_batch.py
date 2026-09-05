import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.db import init_db, SessionLocal, engine
from backend.app.pipeline import run_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=str, required=True)
    parser.add_argument("--batch-id", type=str, default=None)
    args = parser.parse_args()

    init_db(engine)

    with open(args.batch) as f:
        raw_events = json.load(f)

    batch_id = args.batch_id or os.path.basename(args.batch)

    db = SessionLocal()
    try:
        report = run_batch(db, batch_id, raw_events)
    finally:
        db.close()

    print(json.dumps(report, indent=2))
    print(f"events_inserted={report['events_inserted']} events_skipped={report['events_skipped']}", file=sys.stderr)


if __name__ == "__main__":
    main()