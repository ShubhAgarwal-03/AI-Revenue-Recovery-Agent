from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models import Decision
from backend.app.metrics.report import build_metrics_report


def list_batches_in_order(db: Session) -> list[str]:
    rows = (
        db.query(Decision.batch_id, func.min(Decision.created_at).label("first_seen"))
        .group_by(Decision.batch_id)
        .order_by("first_seen")
        .all()
    )
    return [r[0] for r in rows]


def build_metrics_trend(db: Session) -> list[dict]:
    return [build_metrics_report(db, batch_id) for batch_id in list_batches_in_order(db)]