"""Synthetic Benchmark and Topological Scenario Verification Suite.

Tests each controlled synthetic scenario (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT,
CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK) and verifies deterministic reproducibility,
bounded risk scores [0, 100], and explainable scoring breakdowns.

DISCLAIMER: These synthetic benchmark tests validate behavioral and graph pattern detection
on synthetic data. They do NOT evaluate real-world AML or regulatory compliance models.
"""

from __future__ import annotations

import os
import sys
import numpy as np
import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")
for p in (PROJECT_ROOT, ML_DIR, GRAPH_DIR, DATA_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.synthetic.generator import SyntheticDataGenerator
from ml.inference import run_pipeline
from ml.model import RiskLevel


@pytest.fixture
def generator() -> SyntheticDataGenerator:
    return SyntheticDataGenerator(seed=42)


class TestSyntheticScenariosBenchmark:
    """Benchmark tests validating detection performance on each controlled synthetic scenario."""

    def test_benchmark_normal_scenario(self, generator):
        """NORMAL scenario: Dispersed peer-to-peer transfers should yield mostly LOW risk without false cycle/cluster alerts."""
        normal_txs = generator.generate_normal_transactions(num_accounts=20, num_transactions=80)
        res = run_pipeline(normal_txs, random_state=42)

        assert res["pipeline_status"] == "SUCCESS"
        assert res["total_accounts_analyzed"] > 0
        assert res["risk_distribution"]["CRITICAL"] == 0

        # Normal peer-to-peer network should not create coordinated dense clusters
        for acc in res["accounts"]:
            assert "coordinated_network" not in acc["patterns"]
            assert 0.0 <= acc["risk_score"] <= 100.0

    def test_benchmark_fan_in_scenario(self, generator):
        """FAN_IN scenario: Multiple senders funneling funds to a single collector hub."""
        # Mix background normal with fan-in scenario
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        txs.extend(generator.generate_fan_in_scenario(target_account="ACC_FANIN_HUB", num_senders=8))

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        hub_acc = next((a for a in res["accounts"] if a["account_id"] == "ACC_FANIN_HUB"), None)
        assert hub_acc is not None, "Target hub account must be present in analysis"
        assert "fan_in" in hub_acc["patterns"]
        assert hub_acc["graph_features"]["in_degree"] >= 8
        assert any("Fan-in pattern" in ev for ev in hub_acc["evidence"])

    def test_benchmark_fan_out_scenario(self, generator):
        """FAN_OUT scenario: Single source dispersing funds to multiple destination accounts."""
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        txs.extend(generator.generate_fan_out_scenario(source_account="ACC_FANOUT_HUB", num_receivers=8))

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        hub_acc = next((a for a in res["accounts"] if a["account_id"] == "ACC_FANOUT_HUB"), None)
        assert hub_acc is not None
        assert "fan_out" in hub_acc["patterns"]
        assert hub_acc["graph_features"]["out_degree"] >= 8
        assert any("Fan-out pattern" in ev for ev in hub_acc["evidence"])

    def test_benchmark_rapid_movement_scenario(self, generator):
        """RAPID_MOVEMENT scenario: Pass-through intermediary receiving and immediately forwarding funds."""
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        txs.extend(
            generator.generate_rapid_movement_scenario(
                intermediary_account="ACC_RAPID_MID",
                source_account="ACC_RAPID_IN",
                destination_account="ACC_RAPID_OUT",
            )
        )

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        mid_acc = next((a for a in res["accounts"] if a["account_id"] == "ACC_RAPID_MID"), None)
        assert mid_acc is not None
        assert "rapid_movement" in mid_acc["patterns"]
        assert any("Rapid fund movement" in ev for ev in mid_acc["evidence"])

    def test_benchmark_chain_scenario(self, generator):
        """CHAIN scenario: Multi-hop transaction chain A -> B -> C -> D -> E."""
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        txs.extend(generator.generate_chain_scenario(chain_length=5, prefix="ACC_CHAIN"))

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        chain_accounts = [a for a in res["accounts"] if "ACC_CHAIN" in a["account_id"]]
        assert len(chain_accounts) >= 4
        # Middle intermediaries should register multi-hop chain length
        max_chain_len = max(a["graph_features"]["chain_length"] for a in chain_accounts)
        assert max_chain_len >= 3

    def test_benchmark_circular_flow_scenario(self, generator):
        """CIRCULAR_FLOW scenario: Directed cycle A -> B -> C -> A."""
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        cycle_nodes = ["ACC_CYCLE_A", "ACC_CYCLE_B", "ACC_CYCLE_C"]
        txs.extend(generator.generate_circular_flow_scenario(cycle_nodes=cycle_nodes))

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        flagged_cycle_accs = [
            a for a in res["accounts"]
            if a["account_id"] in cycle_nodes and "circular_flow" in a["patterns"]
        ]
        assert len(flagged_cycle_accs) == 3
        for acc in flagged_cycle_accs:
            assert acc["graph_features"]["cycle_detected"] == 1
            assert any("Circular flow pattern" in ev for ev in acc["evidence"])

    def test_benchmark_coordinated_network_scenario(self, generator):
        """COORDINATED_NETWORK scenario: Dense interlocking transaction cluster."""
        txs = generator.generate_normal_transactions(num_accounts=10, num_transactions=30)
        txs.extend(generator.generate_coordinated_network_scenario(network_size=5, prefix="ACC_COORD"))

        res = run_pipeline(txs, random_state=42)
        assert res["pipeline_status"] == "SUCCESS"

        coord_accs = [
            a for a in res["accounts"]
            if "ACC_COORD" in a["account_id"] and "coordinated_network" in a["patterns"]
        ]
        assert len(coord_accs) >= 3


class TestBenchmarkPropertiesAndReproducibility:
    """Verifies strict deterministic reproducibility, score boundaries, and contract integrity."""

    def test_deterministic_reproducibility(self, generator):
        """Same random_state must produce bit-for-bit identical scores, tiers, and breakdowns."""
        dataset = generator.generate_comprehensive_dataset()

        run1 = run_pipeline(dataset, random_state=42)
        run2 = run_pipeline(dataset, random_state=42)

        assert run1["total_accounts_analyzed"] == run2["total_accounts_analyzed"]
        assert run1["risk_distribution"] == run2["risk_distribution"]

        for acc1, acc2 in zip(run1["accounts"], run2["accounts"]):
            assert acc1["account_id"] == acc2["account_id"]
            assert acc1["risk_score"] == acc2["risk_score"]
            assert acc1["risk_level"] == acc2["risk_level"]
            assert acc1["is_anomaly"] == acc2["is_anomaly"]
            assert acc1["patterns"] == acc2["patterns"]
            assert acc1["scoring_breakdown"] == acc2["scoring_breakdown"]
            assert acc1["evidence"] == acc2["evidence"]

    def test_scoring_bounds_and_breakdown_contract(self, generator):
        """Verifies that all composite scores and breakdown components fall strictly in [0.0, 100.0]."""
        dataset = generator.generate_comprehensive_dataset()
        res = run_pipeline(dataset, random_state=42)

        valid_levels = {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}

        for acc in res["accounts"]:
            score = acc["risk_score"]
            assert 0.0 <= score <= 100.0, f"Score {score} out of bounds"
            assert acc["risk_level"] in valid_levels

            breakdown = acc["scoring_breakdown"]
            assert "ml_component" in breakdown
            assert "graph_component" in breakdown
            assert "behavioral_component" in breakdown

            for comp_name, comp_val in breakdown.items():
                assert 0.0 <= comp_val <= 100.0, f"{comp_name} value {comp_val} out of bounds"
