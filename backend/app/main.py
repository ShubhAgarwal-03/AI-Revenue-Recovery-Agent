from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.app.db import init_db, get_db, engine
from backend.app.models import Decision
from backend.app.pipeline import run_batch
from backend.app.metrics.report import build_metrics_report
from backend.app.metrics.trend import build_metrics_trend, list_batches_in_order
from backend.app.metrics.exceptions import build_exceptions
from backend.app.auditor.ledger import decision_to_dict

app = FastAPI(title="AI Revenue Recovery Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db(engine)


@app.post("/batches/{batch_id}/run")
def run_batch_endpoint(batch_id: str, raw_events: list[dict], db: Session = Depends(get_db)):
    return run_batch(db, batch_id, raw_events)


@app.get("/audit")
def get_audit(batch_id: str = None, is_baseline: bool = None, db: Session = Depends(get_db)):
    q = db.query(Decision)
    if batch_id is not None:
        q = q.filter(Decision.batch_id == batch_id)
    if is_baseline is not None:
        q = q.filter(Decision.is_baseline == is_baseline)
    return [decision_to_dict(d) for d in q.all()]


@app.get("/metrics/{batch_id}")
def get_metrics(batch_id: str, db: Session = Depends(get_db)):
    return build_metrics_report(db, batch_id)


@app.get("/metrics-trend")
def get_metrics_trend(db: Session = Depends(get_db)):
    return build_metrics_trend(db)


@app.get("/batches")
def get_batches(db: Session = Depends(get_db)):
    return list_batches_in_order(db)


@app.get("/exceptions/{batch_id}")
def get_exceptions(batch_id: str, db: Session = Depends(get_db)):
    return build_exceptions(db, batch_id)


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")