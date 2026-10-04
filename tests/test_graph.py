"""Unit and Integration Tests for Graph Engine and Network Pattern Detections."""

from __future__ import annotations

import os
import sys
import pytest
import networkx as nx

# Add directories to path
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (PROJECT_ROOT, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from graph import build_transaction_graph, get_graph_summary
from patterns import (
    detect_fan_in,
    detect_fan_out,
    detect_circular_flows,
    detect_transaction_chains,
    detect_rapid_movement,
    detect_coordinated_networks,
    run_all_network_detections,
)
from features import extract_graph_features


class TestGraphCreation:
    """Tests for NetworkX graph construction, nodes, and edges."""

    def test_graph_creation_basic(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "ACC_A", "receiver_id": "ACC_B", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "ACC_B", "receiver_id": "ACC_C", "amount": 50.0, "timestamp": "2026-03-01T10:05:00Z"},
        ]
        g = build_transaction_graph(txs)
        assert isinstance(g, nx.DiGraph)
        assert g.number_of_nodes() == 3
        assert g.number_of_edges() == 2

    def test_node_creation_attributes(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "ACC_X", "receiver_id": "ACC_Y", "amount": 250.0, "timestamp": "2026-03-01T10:00:00Z"}
        ]
        g = build_transaction_graph(txs)
        assert "ACC_X" in g.nodes
        assert "ACC_Y" in g.nodes
        assert g.nodes["ACC_X"]["account_id"] == "ACC_X"
        assert g.nodes["ACC_Y"]["account_id"] == "ACC_Y"

    def test_edge_creation_aggregation(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 200.0, "timestamp": "2026-03-01T11:00:00Z"},
        ]
        g = build_transaction_graph(txs, multi_graph=False)
        assert g.has_edge("ACC_1", "ACC_2")
        edge_data = g["ACC_1"]["ACC_2"]
        assert edge_data["weight"] == 300.0
        assert edge_data["count"] == 2
        assert len(edge_data["transactions"]) == 2

    def test_edge_timestamp_robustness(self):
        # Out-of-order insertion: earlier timestamp inserted after later timestamp
        txs = [
            {"transaction_id": "T2", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 50.0, "timestamp": "2026-03-01T15:30:00Z"},
            {"transaction_id": "T1", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 25.0, "timestamp": "2026-03-01T10:00:00+00:00"},
        ]
        g = build_transaction_graph(txs)
        edge_data = g["ACC_1"]["ACC_2"]
        # The edge timestamp must reflect the latest chronological timestamp
        assert "15:30:00" in edge_data["timestamp"]
        assert isinstance(edge_data["timestamp"], str)


    def test_multi_graph_creation(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "ACC_1", "receiver_id": "ACC_2", "amount": 200.0, "timestamp": "2026-03-01T11:00:00Z"},
        ]
        mg = build_transaction_graph(txs, multi_graph=True)
        assert isinstance(mg, nx.MultiDiGraph)
        assert mg.number_of_edges() == 2

    def test_graph_summary_metrics(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "ACC_A", "receiver_id": "ACC_B", "amount": 10.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "ACC_B", "receiver_id": "ACC_C", "amount": 10.0, "timestamp": "2026-03-01T10:01:00Z"},
        ]
        g = build_transaction_graph(txs)
        summary = get_graph_summary(g)
        assert summary["num_accounts"] == 3
        assert summary["num_edges"] == 2
        assert summary["is_directed"] is True
        assert summary["weakly_connected_components"] == 1


class TestNetworkPatternDetections:
    """Tests for algorithmic detection of suspicious topologies."""

    def test_fan_in_detection(self):
        # 5 distinct senders into HUB
        txs = [
            {"transaction_id": f"T{i}", "sender_id": f"SRC_{i}", "receiver_id": "FANIN_HUB", "amount": 500.0, "timestamp": f"2026-03-01T10:{i:02d}:00Z"}
            for i in range(1, 6)
        ]
        g = build_transaction_graph(txs)
        res = detect_fan_in(g, min_in_degree=4, min_in_out_ratio=2.0)
        assert res.detected is True
        assert "FANIN_HUB" in res.flagged_accounts
        assert len(res.details) == 1
        assert res.details[0]["in_degree"] == 5

    def test_fan_out_detection(self):
        # 1 source sending to 5 distinct receivers
        txs = [
            {"transaction_id": f"T{i}", "sender_id": "FANOUT_HUB", "receiver_id": f"DST_{i}", "amount": 300.0, "timestamp": f"2026-03-01T11:{i:02d}:00Z"}
            for i in range(1, 6)
        ]
        g = build_transaction_graph(txs)
        res = detect_fan_out(g, min_out_degree=4, min_out_in_ratio=2.0)
        assert res.detected is True
        assert "FANOUT_HUB" in res.flagged_accounts
        assert len(res.details) == 1
        assert res.details[0]["out_degree"] == 5

    def test_circular_flow_detection(self):
        # Directed cycle: C1 -> C2 -> C3 -> C1
        txs = [
            {"transaction_id": "T1", "sender_id": "CYC_1", "receiver_id": "CYC_2", "amount": 1000.0, "timestamp": "2026-03-01T12:00:00Z"},
            {"transaction_id": "T2", "sender_id": "CYC_2", "receiver_id": "CYC_3", "amount": 980.0, "timestamp": "2026-03-01T12:15:00Z"},
            {"transaction_id": "T3", "sender_id": "CYC_3", "receiver_id": "CYC_1", "amount": 950.0, "timestamp": "2026-03-01T12:30:00Z"},
        ]
        g = build_transaction_graph(txs)
        res = detect_circular_flows(g, min_cycle_length=3, max_cycle_length=5)
        assert res.detected is True
        assert set(res.flagged_accounts) == {"CYC_1", "CYC_2", "CYC_3"}

    def test_chain_detection(self):
        # Linear chain: H1 -> H2 -> H3 -> H4 -> H5 (4 hops)
        txs = [
            {"transaction_id": "T1", "sender_id": "HOP_1", "receiver_id": "HOP_2", "amount": 2000.0, "timestamp": "2026-03-01T13:00:00Z"},
            {"transaction_id": "T2", "sender_id": "HOP_2", "receiver_id": "HOP_3", "amount": 1900.0, "timestamp": "2026-03-01T13:10:00Z"},
            {"transaction_id": "T3", "sender_id": "HOP_3", "receiver_id": "HOP_4", "amount": 1850.0, "timestamp": "2026-03-01T13:20:00Z"},
            {"transaction_id": "T4", "sender_id": "HOP_4", "receiver_id": "HOP_5", "amount": 1800.0, "timestamp": "2026-03-01T13:30:00Z"},
        ]
        g = build_transaction_graph(txs)
        res = detect_transaction_chains(g, min_hops=3)
        assert res.detected is True
        assert "HOP_2" in res.flagged_accounts
        assert "HOP_3" in res.flagged_accounts

    def test_rapid_movement_detection(self):
        # MID receives 5000 and forwards 4800 within 5 minutes (300 seconds)
        txs = [
            {"transaction_id": "T1", "sender_id": "SRC", "receiver_id": "MID", "amount": 5000.0, "timestamp": "2026-03-01T14:00:00Z"},
            {"transaction_id": "T2", "sender_id": "MID", "receiver_id": "DST", "amount": 4800.0, "timestamp": "2026-03-01T14:05:00Z"},
        ]
        g = build_transaction_graph(txs)
        res = detect_rapid_movement(g, time_window_seconds=1800.0)
        assert res.detected is True
        assert "MID" in res.flagged_accounts
        assert res.details[0]["fastest_latency_seconds"] == 300.0

    def test_coordinated_network_detection(self):
        # 3 accounts heavily interconnected (clique-like)
        txs = [
            {"transaction_id": "T1", "sender_id": "CL_1", "receiver_id": "CL_2", "amount": 100.0, "timestamp": "2026-03-01T15:00:00Z"},
            {"transaction_id": "T2", "sender_id": "CL_2", "receiver_id": "CL_3", "amount": 100.0, "timestamp": "2026-03-01T15:05:00Z"},
            {"transaction_id": "T3", "sender_id": "CL_3", "receiver_id": "CL_1", "amount": 100.0, "timestamp": "2026-03-01T15:10:00Z"},
            {"transaction_id": "T4", "sender_id": "CL_2", "receiver_id": "CL_1", "amount": 100.0, "timestamp": "2026-03-01T15:15:00Z"},
        ]
        g = build_transaction_graph(txs)
        res = detect_coordinated_networks(g, min_cluster_size=3)
        assert res.detected is True
        assert set(res.flagged_accounts) == {"CL_1", "CL_2", "CL_3"}


class TestGraphFeatures:
    """Tests for account-level graph feature extraction."""

    def test_extract_graph_features(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "C", "receiver_id": "B", "amount": 200.0, "timestamp": "2026-03-01T10:05:00Z"},
        ]
        g = build_transaction_graph(txs)
        df = extract_graph_features(g)
        assert "B" in df.index
        assert df.loc["B", "in_degree"] == 2
        assert df.loc["B", "out_degree"] == 0
        assert df.loc["B", "weighted_in_degree"] == 300.0
        assert df.loc["B", "unique_counterparties"] == 2
