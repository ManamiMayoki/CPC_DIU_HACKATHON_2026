"""HTTP API for the ML risk pipeline (served by uvicorn in the ml-engine container)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from inference import PROJECT_ROOT, run_pipeline

SAMPLE_PATH = os.path.join(PROJECT_ROOT, "data", "synthetic", "transactions_sample.json")

app = FastAPI(title="Cygnus ML Engine", version="1.0.0")


class TransactionBatch(BaseModel):
    transactions: List[Dict[str, Any]]
    contamination: float = 0.10


def _to_json(result: Dict[str, Any]) -> Any:
    # Feature rows come out of pandas with numpy scalars, which FastAPI cannot encode directly
    return json.loads(json.dumps(result, default=lambda v: v.item() if hasattr(v, "item") else str(v)))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "online", "service": "ml-engine"}


@app.post("/pipeline")
def pipeline(batch: TransactionBatch) -> Any:
    return _to_json(run_pipeline(batch.transactions, contamination=batch.contamination, random_state=42))


@app.get("/pipeline/sample")
def pipeline_sample() -> Any:
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        transactions = json.load(f)
    return _to_json(run_pipeline(transactions, contamination=0.10, random_state=42))
