"""Unit and Integration Tests for ML Feature Engineering, Anomaly Detection, and Risk Scoring."""

from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd
import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (PROJECT_ROOT, ML_DIR, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.features import extract_transaction_features, build_ml_feature_vector
from ml.model import AnomalyDetector, ExplainableRiskScorer, RiskLevel
from ml.inference import generate_account_evidence, run_pipeline
from graph import build_transaction_graph
from features import extract_graph_features


class TestMLFeatures:
    """Tests for behavioral feature calculation and vector building."""

    def test_extract_transaction_features(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
            {"transaction_id": "T2", "sender_id": "A", "receiver_id": "C", "amount": 200.0, "timestamp": "2026-03-01T10:30:00Z"},
        ]
        df = extract_transaction_features(txs)
        assert "A" in df.index
        assert df.loc["A", "transaction_count"] == 2
        assert df.loc["A", "sent_count"] == 2
        assert df.loc["A", "received_count"] == 0
        assert df.loc["A", "total_outgoing"] == 300.0
        assert df.loc["A", "average_transaction_amount"] == 150.0
        assert df.loc["A", "maximum_transaction_amount"] == 200.0
        assert df.loc["A", "unique_receivers"] == 2

    def test_build_ml_feature_vector(self):
        txs = [
            {"transaction_id": "T1", "sender_id": "A", "receiver_id": "B", "amount": 100.0, "timestamp": "2026-03-01T10:00:00Z"},
        ]
        tx_f = extract_transaction_features(txs)
        g = build_transaction_graph(txs)
        gf = extract_graph_features(g)
        combined = build_ml_feature_vector(tx_f, gf)
        assert not combined.empty
        assert "in_degree" in combined.columns
        assert "transaction_count" in combined.columns


class TestAnomalyDetector:
    """Tests for unsupervised Isolation Forest model, fitting, scoring, and reproducibility."""

    @pytest.fixture
    def sample_features(self) -> pd.DataFrame:
        np.random.seed(42)
        # 30 normal points, 2 anomalous outliers
        normal_data = np.random.normal(loc=10.0, scale=1.0, size=(30, 4))
        outlier_data = np.array([[100.0, 150.0, 200.0, 300.0], [90.0, 110.0, 180.0, 250.0]])
        full_data = np.vstack([normal_data, outlier_data])
        index = [f"ACC_{i:02d}" for i in range(32)]
        cols = ["f1", "f2", "f3", "f4"]
        return pd.DataFrame(full_data, index=index, columns=cols)

    def test_model_training_and_prediction(self, sample_features):
        detector = AnomalyDetector(contamination=0.1, random_state=42)
        assert detector.is_fitted is False
        detector.fit(sample_features)
        assert detector.is_fitted is True

        preds = detector.predict(sample_features)
        assert len(preds) == len(sample_features)
        assert set(preds).issubset({-1, 1})

    def test_anomaly_score_and_normalized_risk(self, sample_features):
        detector = AnomalyDetector(contamination=0.1, random_state=42)
        detector.fit(sample_features)
        scores_df = detector.compute_anomaly_scores(sample_features)

        assert "is_anomaly" in scores_df.columns
        assert "ml_anomaly_score" in scores_df.columns
        assert (scores_df["ml_anomaly_score"] >= 0.0).all()
        assert (scores_df["ml_anomaly_score"] <= 100.0).all()

        # The outliers (ACC_30, ACC_31) should have high anomaly scores
        assert scores_df.loc["ACC_30", "ml_anomaly_score"] > scores_df.loc["ACC_00", "ml_anomaly_score"]

    def test_reproducibility(self, sample_features):
        # Two models with same random_state must yield identical scores
        m1 = AnomalyDetector(contamination=0.1, random_state=42).fit(sample_features)
        s1 = m1.compute_anomaly_scores(sample_features)["ml_anomaly_score"].values

        m2 = AnomalyDetector(contamination=0.1, random_state=42).fit(sample_features)
        s2 = m2.compute_anomaly_scores(sample_features)["ml_anomaly_score"].values

        np.testing.assert_array_almost_equal(s1, s2)

    def test_risk_levels(self):
        assert RiskLevel.from_score(95.0) == RiskLevel.CRITICAL
        assert RiskLevel.from_score(75.0) == RiskLevel.HIGH
        assert RiskLevel.from_score(55.0) == RiskLevel.MEDIUM
        assert RiskLevel.from_score(25.0) == RiskLevel.LOW


class TestExplainableRiskScoringAndEvidence:
    """Tests for composite scoring and evidence generation."""

    def test_composite_scoring(self):
        scorer = ExplainableRiskScorer()
        score, level, breakdown = scorer.compute_composite_risk(
            account_id="ACC_TEST",
            ml_score=80.0,
            is_ml_anomaly=True,
            feature_row={"transaction_velocity": 12.0, "incoming_outgoing_ratio": 10.0, "maximum_transaction_amount": 6000.0},
            pattern_flags={"circular_flow": True, "rapid_movement": True},
        )
        assert 0.0 <= score <= 100.0
        assert level in {RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}
        assert "ml_component" in breakdown
        assert "graph_component" in breakdown
        assert "behavioral_component" in breakdown

    def test_evidence_generation(self):
        evidence = generate_account_evidence(
            account_id="ACC_EV",
            features={"in_degree": 6, "out_degree": 1, "transaction_velocity": 15.0, "cycle_count": 2},
            active_patterns=["fan_in", "circular_flow"],
            is_ml_anomaly=True,
            ml_score=85.0,
            pattern_details={},
        )
        assert len(evidence) >= 3
        text = " ".join(evidence)
        assert "Circular flow pattern" in text
        assert "Fan-in pattern" in text
        assert "High transaction velocity" in text
