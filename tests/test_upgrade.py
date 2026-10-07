"""Tests for the structuring detector, time-ordered loop check and AI Investigator briefing."""

from __future__ import annotations

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (PROJECT_ROOT, ML_DIR, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from graph import build_transaction_graph
from patterns import detect_circular_flows, detect_structuring
from ml.inference import run_pipeline


def _tx(tx_id, sender, receiver, amount, timestamp):
    return {"transaction_id": tx_id, "sender_id": sender, "receiver_id": receiver, "amount": amount, "timestamp": timestamp}


def test_structuring_flags_repeated_near_threshold_transfers():
    txs = [
        _tx(f"S{i}", "SPLITTER", "COLLECTOR", amount, f"2026-03-01T{10 + i}:00:00Z")
        for i, amount in enumerate([9500, 9800, 9650, 9900])
    ]
    result = detect_structuring(build_transaction_graph(txs))
    roles = {d["account_id"]: d["role"] for d in result.details}
    assert roles == {"SPLITTER": "splitter", "COLLECTOR": "collector"}
    splitter = next(d for d in result.details if d["account_id"] == "SPLITTER")
    assert splitter["near_threshold_count"] == 4


def test_structuring_ignores_amounts_far_below_threshold_or_spread_out():
    small = [_tx(f"A{i}", "X", "Y", 2000, f"2026-03-01T{10 + i}:00:00Z") for i in range(5)]
    spread = [_tx(f"B{i}", "P", "Q", 9700, f"2026-03-0{1 + 2 * i}T10:00:00Z") for i in range(4)]
    assert not detect_structuring(build_transaction_graph(small + spread)).detected


def test_circular_flow_requires_time_ordered_hops():
    # Same loop A -> B -> C -> A, but each hop happens before the money could have arrived.
    out_of_order = [
        _tx("C1", "C", "A", 950, "2026-03-01T09:00:00Z"),
        _tx("C2", "B", "C", 970, "2026-03-01T09:30:00Z"),
        _tx("C3", "A", "B", 1000, "2026-03-03T10:00:00Z"),
    ]
    assert not detect_circular_flows(build_transaction_graph(out_of_order)).detected

    in_order = [
        _tx("D1", "A", "B", 1000, "2026-03-01T10:00:00Z"),
        _tx("D2", "B", "C", 970, "2026-03-01T10:10:00Z"),
        _tx("D3", "C", "A", 950, "2026-03-01T10:20:00Z"),
    ]
    result = detect_circular_flows(build_transaction_graph(in_order))
    assert len(result.details) == 1
    assert result.details[0]["length"] == 3


def test_investigation_is_built_from_detected_evidence():
    txs = [_tx(f"S{i}", "SPLITTER", "COLLECTOR", 9600 + i * 50, f"2026-03-01T{10 + i}:00:00Z") for i in range(4)]
    txs += [_tx("N1", "SPLITTER", "SHOP", 300, "2026-03-02T10:00:00Z")]
    result = run_pipeline(txs)
    report = next(a for a in result["accounts"] if a["account_id"] == "SPLITTER")
    inv = report["investigation"]
    assert "structuring" in report["patterns"]
    assert inv["typology"] == "Structuring (smurfing)"
    assert inv["generated_by"] == "rule-based"
    assert any("just under BDT 10,000" in f for f in inv["key_findings"])
    assert "COLLECTOR" in inv["related_accounts"]
    assert inv["next_steps"]

    shop = next(a for a in result["accounts"] if a["account_id"] == "SHOP")
    assert shop["investigation"]["typology"] == "No suspicious typology"
