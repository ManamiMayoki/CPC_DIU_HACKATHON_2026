"""ML Anomaly Detection and Explainable Risk Scoring Engine.

Implements unsupervised anomaly detection using scikit-learn's Isolation Forest,
along with a mathematically grounded, robust percentile/MAD-calibrated multi-signal
risk scoring pipeline.

DISCLAIMER: All thresholds (LOW, MEDIUM, HIGH, CRITICAL) and risk scoring weights
are prototype heuristics configured for synthetic hackathon data. They do NOT represent
official banking, AML, or regulatory risk thresholds.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler


class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_score(cls, score: float) -> str:
        """Maps a 0-100 normalized risk score to an explainable risk tier.

        Prototype Thresholds:
        - 0.0 <= score < 40.0: LOW
        - 40.0 <= score < 70.0: MEDIUM
        - 70.0 <= score < 90.0: HIGH
        - 90.0 <= score <= 100.0: CRITICAL
        """
        if score >= 90.0:
            return cls.CRITICAL
        elif score >= 70.0:
            return cls.HIGH
        elif score >= 40.0:
            return cls.MEDIUM
        return cls.LOW


class AnomalyDetector:
    """Unsupervised Anomaly Detector utilizing Isolation Forest.

    Provides reproducible fitting, outlier prediction, decision score extraction,
    and robust MAD/percentile-rank normalization to an explainable 0-100 risk scale.
    """

    def __init__(
        self,
        contamination: Union[str, float] = 0.1,
        random_state: int = 42,
        n_estimators: int = 150,
    ) -> None:
        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=self.n_estimators,
        )
        self.scaler = RobustScaler()
        self.is_fitted: bool = False
        self.feature_names_: List[str] = []
        self._median_raw_score: float = 0.0
        self._mad_scale: float = 0.1
        self._min_raw_score: float = -0.5
        self._max_raw_score: float = 0.5
        self._baseline_raw_scores: np.ndarray = np.array([])

    def fit(self, X: Union[pd.DataFrame, np.ndarray]) -> "AnomalyDetector":
        """Fits the Isolation Forest on the account feature matrix and computes robust baseline statistics."""
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            values = X.values
        else:
            values = np.asarray(X)
            self.feature_names_ = [f"f_{i}" for i in range(values.shape[1])]

        if values.shape[0] == 0:
            raise ValueError("Cannot fit AnomalyDetector on empty feature matrix (0 rows).")

        scaled_vals = self.scaler.fit_transform(values)
        self.model.fit(scaled_vals)
        self.is_fitted = True

        # Store baseline decision scores for robust calibration
        raw_scores = self.model.decision_function(scaled_vals)
        self._baseline_raw_scores = raw_scores

        med = float(np.median(raw_scores)) if len(raw_scores) > 0 else 0.0
        mad = float(np.median(np.abs(raw_scores - med))) if len(raw_scores) > 0 else 0.1
        mad_scale = 1.4826 * mad

        # Fallback if MAD is near zero
        if mad_scale < 1e-4:
            std = float(np.std(raw_scores)) if len(raw_scores) > 0 else 0.1
            mad_scale = max(std, 0.05)

        self._median_raw_score = med
        self._mad_scale = mad_scale
        self._min_raw_score = float(np.min(raw_scores)) if len(raw_scores) > 0 else -0.5
        self._max_raw_score = float(np.max(raw_scores)) if len(raw_scores) > 0 else 0.5

        return self

    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Predicts anomaly status: -1 for anomaly, 1 for normal."""
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector must be fitted before calling predict().")
        values = X.values if isinstance(X, pd.DataFrame) else np.asarray(X)
        scaled_vals = self.scaler.transform(values)
        return self.model.predict(scaled_vals)

    def decision_function(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Returns raw decision function scores.

        Lower values denote higher abnormality.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector must be fitted before calling decision_function().")
        values = X.values if isinstance(X, pd.DataFrame) else np.asarray(X)
        scaled_vals = self.scaler.transform(values)
        return self.model.decision_function(scaled_vals)

    def compute_anomaly_scores(
        self,
        X: Union[pd.DataFrame, np.ndarray],
    ) -> pd.DataFrame:
        """Computes raw anomaly scores, outlier flags, and robustly normalized risk scores (0-100).

        Normalization Methodology:
        Combines robust Z-score (deviation from median scaled by MAD) mapped through a logistic
        sigmoid with empirical percentile rank relative to baseline scores. This avoids
        brittle min/max normalization being skewed by extreme single outliers.
        """
        if not self.is_fitted:
            raise RuntimeError("AnomalyDetector must be fitted before calling compute_anomaly_scores().")

        raw_scores = self.decision_function(X)
        preds = self.predict(X)

        n = len(raw_scores)
        if n == 0:
            return pd.DataFrame(columns=["is_anomaly", "raw_decision_score", "ml_anomaly_score"])

        # Decision boundary-aligned robust normalization:
        # In Isolation Forest: s >= 0 denotes inliers (normal), s < 0 denotes outliers (anomalous).
        # We use robust spread (MAD / std) centered at the decision threshold (0.0).
        spread = max(self._mad_scale, 0.05)
        d = -raw_scores / spread

        # Smooth boundary-calibrated mapping:
        # Inliers (s >= 0): mapped into [5.0, 38.0] (LOW tier)
        # Outliers (s < 0): mapped into [50.0, 98.0] (MEDIUM/HIGH/CRITICAL tiers)
        inlier_scores = 38.0 * np.exp(d)
        outlier_scores = 50.0 + 48.0 * np.tanh(0.75 * d)

        risk_scores = np.where(raw_scores >= 0.0, inlier_scores, outlier_scores)
        risk_scores = np.clip(np.round(risk_scores, 2), 0.0, 100.0)

        index = X.index if isinstance(X, pd.DataFrame) else range(len(preds))
        res_df = pd.DataFrame(
            {
                "is_anomaly": [bool(p == -1) for p in preds],
                "raw_decision_score": np.round(raw_scores, 4),
                "ml_anomaly_score": risk_scores,
            },
            index=index,
        )
        return res_df



class ExplainableRiskScorer:
    """Combines ML anomaly scores, graph topology signals, and behavioral indicators.

    Transparent Scoring Composition:
    1. ML Anomaly Score (Weight: 40% / 0.40)
       - Derived directly from Isolation Forest multivariate outlier density.
    2. Graph Suspicious Topology Signals (Weight: 40% / 0.40)
       - Circular flows (cycles): up to 35 pts
       - Rapid fund movement (passthrough): up to 30 pts
       - Coordinated network cluster membership: up to 40 pts
       - Structuring (near-threshold splitting): up to 30 pts
       - Fan-in collector pattern: up to 25 pts
       - Fan-out distributor pattern: up to 25 pts
       - Long chain participation (>= 3 hops): up to 20 pts
       - Suspicious neighbor exposure: up to 15 pts
       (Normalized to max 100 before weighting).
    3. Behavioral & Flow Consistency Indicators (Weight: 20% / 0.20)
       - Population-calibrated velocity (p75 / p90 thresholds): up to 30 pts
       - Flow imbalance & depletion: up to 25 pts
       - Transaction amount deviation: up to 25 pts
       - Flow passthrough / layering consistency: up to 20 pts
       - Counterparty concentration: up to 15 pts
       (Normalized to max 100 before weighting).

    Final Risk Score = (0.40 * ML) + (0.40 * Graph) + (0.20 * Behavioral)

    Graph-evidence floor: the final score is never lower than GRAPH_EVIDENCE_FLOOR x Graph.
    The ML component is an unsupervised outlier score, so an account that looks like several
    others (four mules doing the same thing) is not an outlier and scores low on ML even when
    the graph evidence is overwhelming. The floor stops that dilution: strong, corroborated
    network evidence alone is enough for HIGH, while CRITICAL still needs the other signals.
    """

    GRAPH_EVIDENCE_FLOOR: float = 0.75
    BUSINESS_TIERS = ("agent", "merchant")
    BUSINESS_AS_USUAL_PATTERNS = ("fan_in", "fan_out", "rapid_movement")

    WEIGHT_ML: float = 0.40
    WEIGHT_GRAPH: float = 0.40
    WEIGHT_BEHAVIORAL: float = 0.20

    def __init__(
        self,
        weight_ml: float = WEIGHT_ML,
        weight_graph: float = WEIGHT_GRAPH,
        weight_behavioral: float = WEIGHT_BEHAVIORAL,
        feature_df: Optional[pd.DataFrame] = None,
    ) -> None:
        total = weight_ml + weight_graph + weight_behavioral
        self.w_ml = weight_ml / total
        self.w_graph = weight_graph / total
        self.w_beh = weight_behavioral / total
        self.baselines: Dict[str, float] = {}

        if feature_df is not None and not feature_df.empty:
            self.calibrate(feature_df)

    def calibrate(self, feature_df: pd.DataFrame) -> None:
        """Derives robust population percentile thresholds (p75, p90) from current dataset features."""
        if feature_df.empty:
            return

        def safe_percentile(col: str, p: float, default: float) -> float:
            if col in feature_df.columns:
                vals = feature_df[col].dropna().values
                if len(vals) > 0:
                    return float(np.percentile(vals, p))
            return default

        self.baselines = {
            "velocity_p75": safe_percentile("transaction_velocity", 75, 5.0),
            "velocity_p90": safe_percentile("transaction_velocity", 90, 10.0),
            "max_amt_p75": safe_percentile("maximum_transaction_amount", 75, 1500.0),
            "max_amt_p90": safe_percentile("maximum_transaction_amount", 90, 4000.0),
            "passthrough_p75": safe_percentile("passthrough_ratio", 75, 0.70),
            "imbalance_p75": safe_percentile("flow_imbalance_magnitude", 75, 0.75),
            "diversity_p25": safe_percentile("counterparty_diversity", 25, 0.50),
        }

    def compute_composite_risk(
        self,
        account_id: str,
        ml_score: float,
        is_ml_anomaly: bool,
        feature_row: Dict[str, Any],
        pattern_flags: Dict[str, bool],
        account_tier: str = "personal",
    ) -> Tuple[float, str, Dict[str, float]]:
        """Calculates final explainable risk score (0-100) and risk tier.

        account_tier is the KYC account type. For agents and merchants, collecting from many
        customers, paying out to many and turning money around quickly is the business itself,
        so fan-in, fan-out and rapid movement are not counted as suspicious for those tiers
        (the Phase 2 bias check showed they otherwise flag almost every legitimate agent).
        """
        if account_tier in self.BUSINESS_TIERS:
            pattern_flags = {k: v for k, v in pattern_flags.items() if k not in self.BUSINESS_AS_USUAL_PATTERNS}
        # 1. ML component (0-100)
        c_ml = float(ml_score)

        # 2. Graph topology component (0-100)
        graph_pts = 0.0
        if pattern_flags.get("circular_flow", False) or feature_row.get("cycle_detected", 0) > 0:
            graph_pts += 35.0
        if pattern_flags.get("rapid_movement", False):
            graph_pts += 30.0
        if pattern_flags.get("coordinated_network", False):
            graph_pts += 40.0
        if pattern_flags.get("structuring", False) or feature_row.get("structuring_detected", 0) > 0:
            graph_pts += 30.0
        if pattern_flags.get("fan_in", False):
            graph_pts += 25.0
        if pattern_flags.get("fan_out", False):
            graph_pts += 25.0
        if feature_row.get("chain_length", 0) >= 3:
            graph_pts += 20.0
        if feature_row.get("suspicious_neighbor_count", 0) >= 2:
            graph_pts += 15.0

        c_graph = min(100.0, graph_pts)

        # 3. Behavioral & Flow Consistency component (0-100)
        beh_pts = 0.0

        # Velocity check: calibrated against population percentiles
        velocity = feature_row.get("transaction_velocity", 0.0)
        vel_p90 = self.baselines.get("velocity_p90", 10.0)
        vel_p75 = self.baselines.get("velocity_p75", 5.0)
        if velocity >= vel_p90:
            beh_pts += 30.0
        elif velocity >= vel_p75:
            beh_pts += 15.0

        # Flow imbalance check
        ratio = feature_row.get("incoming_outgoing_ratio", 1.0)
        imbalance_mag = feature_row.get("flow_imbalance_magnitude", 0.0)
        if ratio > 5.0 or ratio < 0.2 or imbalance_mag >= self.baselines.get("imbalance_p75", 0.75):
            beh_pts += 25.0

        # Amount deviation check: calibrated against population percentiles
        max_amt = feature_row.get("maximum_transaction_amount", 0.0)
        amt_p90 = self.baselines.get("max_amt_p90", 4000.0)
        amt_p75 = self.baselines.get("max_amt_p75", 1500.0)
        if max_amt >= amt_p90:
            beh_pts += 25.0
        elif max_amt >= amt_p75:
            beh_pts += 12.0

        # Layering flow passthrough consistency check
        passthrough = feature_row.get("passthrough_ratio", 0.0)
        if passthrough >= self.baselines.get("passthrough_p75", 0.70) and feature_row.get("total_incoming", 0.0) > 500:
            beh_pts += 20.0

        # Counterparty concentration / low diversity with multi-transaction activity
        diversity = feature_row.get("counterparty_diversity", 1.0)
        tx_count = feature_row.get("transaction_count", 1)
        if tx_count >= 3 and diversity <= self.baselines.get("diversity_p25", 0.50):
            beh_pts += 15.0

        c_beh = min(100.0, beh_pts)

        # Weighted combination
        weighted_score = (self.w_ml * c_ml) + (self.w_graph * c_graph) + (self.w_beh * c_beh)
        final_score = max(weighted_score, self.GRAPH_EVIDENCE_FLOOR * c_graph)
        final_score = round(min(100.0, max(0.0, final_score)), 2)

        tier = RiskLevel.from_score(final_score)
        breakdown = {
            "ml_component": round(c_ml, 2),
            "graph_component": round(c_graph, 2),
            "behavioral_component": round(c_beh, 2),
        }

        return final_score, tier, breakdown
