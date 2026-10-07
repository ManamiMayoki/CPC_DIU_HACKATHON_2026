"""HTTP API for the Graph Engine (served by uvicorn in the graph-engine container)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from engine import GraphEngine, PROJECT_ROOT

SAMPLE_PATH = os.path.join(PROJECT_ROOT, "data", "synthetic", "transactions_sample.json")

app = FastAPI(title="Cygnus Graph Engine", version="1.0.0")


class TransactionBatch(BaseModel):
    transactions: List[Dict[str, Any]]


def _to_json(result: Dict[str, Any]) -> Any:
    # Feature tables come out of pandas with numpy scalars, which FastAPI cannot encode directly
    return json.loads(json.dumps(result, default=lambda v: v.item() if hasattr(v, "item") else str(v)))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "online", "service": "graph-engine"}


@app.post("/analyze")
def analyze(batch: TransactionBatch) -> Any:
    return _to_json(GraphEngine().analyze(batch.transactions))


@app.get("/analyze/sample")
def analyze_sample() -> Any:
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        transactions = json.load(f)
    return _to_json(GraphEngine().analyze(transactions))
