import hashlib

from sqlalchemy.orm import Session

from backend.app.models import Event


def compute_dedup_key(raw: dict, batch_id: str) -> str:
    parts = [
        batch_id,
        str(raw.get("event_type")),
        str(raw.get("customer_id")),
        str(raw.get("amount_inr")),
        str(raw.get("decline_code")),
        str(raw.get("gateway_error")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def ingest_events(db: Session, batch_id: str, raw_events: list[dict]):
    """Ingest raw event dicts, skipping any whose dedup_key already exists.

    Returns (inserted_events, inserted_count, skipped_count).
    """
    inserted = []
    skipped = 0
    for raw in raw_events:
        dedup_key = compute_dedup_key(raw, batch_id)
        exists = db.query(Event).filter(Event.dedup_key == dedup_key).first()
        if exists is not None:
            skipped += 1
            continue
        event = Event(
            batch_id=batch_id,
            event_type=raw["event_type"],
            amount_inr=raw["amount_inr"],
            customer_id=raw["customer_id"],
            decline_code=raw.get("decline_code"),
            gateway_error=raw.get("gateway_error"),
            time_of_abandonment_sec=raw.get("time_of_abandonment_sec"),
            context=raw.get("context", {}) or {},
            ground_truth_category=raw.get("ground_truth_category"),
            dedup_key=dedup_key,
        )
        db.add(event)
        inserted.append(event)
    db.commit()
    for e in inserted:
        db.refresh(e)
    return inserted, len(inserted), skipped