"""Regression tests for bugs found during the pre-submission review."""

from __future__ import annotations

import os
import subprocess
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (PROJECT_ROOT, ML_DIR, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.inference import run_pipeline


def test_mixed_timezone_timestamps_do_not_crash_pipeline():
    """Naive ISO, 'Z'-suffixed ISO and epoch timestamps in one batch used to raise TypeError."""
    transactions = [
        {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
        {"transaction_id": "T2", "sender_id": "B", "receiver_id": "C", "amount": 95.0, "timestamp": "2026-03-01T10:05:00"},
        {"transaction_id": "T3", "sender_id": "C", "receiver_id": "A", "amount": 90.0, "timestamp": 1772360000},
    ]
    result = run_pipeline(transactions)
    assert result["pipeline_status"] == "SUCCESS"
    assert result["total_accounts_analyzed"] == 3


def test_risk_scores_identical_across_python_hash_seeds():
    """Cycle detection used to depend on PYTHONHASHSEED, so scores changed on every restart."""
    script = (
        "import json, sys; sys.path[:0] = ['.', 'ml', 'graph-engine'];"
        "from ml.inference import run_pipeline;"
        "tx = json.load(open('data/synthetic/transactions_sample.json'));"
        "r = run_pipeline(tx);"
        "print(json.dumps([(a['account_id'], a['risk_score']) for a in r['accounts']]))"
    )
    outputs = set()
    for seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        proc = subprocess.run(
            [sys.executable, "-c", script], cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, check=True
        )
        outputs.add(proc.stdout)
    assert len(outputs) == 1
