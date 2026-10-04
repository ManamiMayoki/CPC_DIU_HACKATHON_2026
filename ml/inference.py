"""Inference Pipeline, Evidence Generation, and Member 1 Integration Contract.

Executes the end-to-end detection pipeline from raw transactions to structured,
explainable risk reports without encroaching on Member 1's backend/frontend scope.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

# Support imports across workspace
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (CURRENT_DIR, PROJECT_ROOT, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from ml.validation import validate_transactions, ValidationResult
from ml.features import extract_transaction_features, build_ml_feature_vector
from ml.model import AnomalyDetector, ExplainableRiskScorer, RiskLevel
from engine import GraphEngine


def generate_account_evidence(
    account_id: str,
    features: Dict[str, Any],
    active_patterns: List[str],
    is_ml_anomaly: bool,
    ml_score: float,
    pattern_details: Dict[str, Any],
) -> List[str]:
    """Generates human-readable, auditable evidence statements strictly derived from calculated metrics.

    Never invents uncalculated or fabricated evidence.
    """
    evidence: List[str] = []

    # 1. Graph Pattern Evidence
    if "circular_flow" in active_patterns:
        c_count = int(features.get("cycle_count", 1))
        evidence.append(
            f"Circular flow pattern detected: account participates in {c_count} directed cycle(s)."
        )

    if "rapid_movement" in active_patterns:
        # Check details for fastest latency
        rapid_info = pattern_details.get("rapid_movement", {})
        latency = rapid_info.get("fastest_latency_seconds")
        if latency is not None:
            evidence.append(
                f"Rapid fund movement detected: funds forwarded within {int(latency)} seconds of receipt."
            )
        else:
            evidence.append("Rapid fund movement detected: funds forwarded shortly after receipt.")

    if "fan_in" in active_patterns:
        in_deg = features.get("in_degree", 0)
        out_deg = features.get("out_degree", 0)
        evidence.append(
            f"Fan-in pattern detected: received funds from {in_deg} distinct senders with only {out_deg} outgoing counterparty."
        )

    if "fan_out" in active_patterns:
        in_deg = features.get("in_degree", 0)
        out_deg = features.get("out_degree", 0)
        evidence.append(
            f"Fan-out pattern detected: dispersed funds to {out_deg} distinct receivers from {in_deg} incoming source(s)."
        )

    if "coordinated_network" in active_patterns:
        evidence.append(
            "Coordinated network membership: account is part of a densely interconnected transaction cluster."
        )

    chain_len = features.get("chain_length", 0)
    if chain_len >= 3:
        evidence.append(
            f"Transaction chain detected: participates in a multi-hop path spanning {chain_len} hops."
        )

    # 2. Behavioral Indicators Evidence
    velocity = features.get("transaction_velocity", 0.0)
    if velocity >= 10.0:
        evidence.append(
            f"High transaction velocity: {round(velocity, 1)} transactions per hour."
        )

    ratio = features.get("incoming_outgoing_ratio", 1.0)
    if ratio >= 8.0:
        evidence.append(
            f"Severe fund imbalance: incoming funds exceed outgoing by {round(ratio, 1)}x."
        )
    elif ratio <= 0.15 and features.get("total_outgoing", 0.0) > 0:
        evidence.append("Severe fund depletion: outgoing funds heavily outweigh incoming receipts.")

    suspicious_neighbors = features.get("suspicious_neighbor_count", 0)
    if suspicious_neighbors >= 2:
        evidence.append(
            f"High network exposure: directly connected to {suspicious_neighbors} accounts with flagged patterns."
        )

    passthrough = features.get("passthrough_ratio", 0.0)
    if passthrough >= 0.85 and features.get("total_incoming", 0.0) > 1000:
        evidence.append(
            f"High layering passthrough ratio: {round(passthrough * 100, 1)}% of incoming funds forwarded onward."
        )

    diversity = features.get("counterparty_diversity", 1.0)
    if features.get("transaction_count", 0) >= 4 and diversity <= 0.40:
        evidence.append(
            f"High counterparty concentration: transactions restricted to only {int(features.get('unique_counterparties', 1))} counterparty(s)."
        )


    # 3. ML Model Outlier Evidence
    if is_ml_anomaly:
        evidence.append(
            f"Statistical multivariate anomaly flagged by Isolation Forest (anomaly score: {ml_score}/100)."
        )

    if not evidence:
        evidence.append("Normal transactional behavior: no anomalous patterns or metric deviations detected.")

    return evidence


def run_pipeline(
    transactions: Union[List[Dict[str, Any]], pd.DataFrame],
    contamination: float = 0.1,
    random_state: int = 42,
    strict_validation: bool = False,
) -> Dict[str, Any]:
    """Complete execution pipeline returning the structured contract for Member 1.

    Returns:
        Structured output containing:
        - pipeline_status: str
        - total_accounts_analyzed: int
        - validation_summary: dict
        - graph_summary: dict
        - accounts: List[Dict[str, Any]] (sorted by risk_score descending)
        - risk_distribution: dict
    """
    # 1. Validation
    val_res: ValidationResult = validate_transactions(transactions, strict=strict_validation)
    if not val_res.valid_transactions:
        return {
            "pipeline_status": "FAILED",
            "error": "Dataset validation failed: no valid transactions.",
            "validation_summary": {
                "is_valid": val_res.is_valid,
                "valid_count": val_res.valid_count,
                "invalid_count": val_res.invalid_count,
                "errors": val_res.errors,
            },
            "accounts": [],
            "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
        }

    valid_txs = val_res.valid_transactions

    # 2. Graph Engine Analysis
    graph_engine = GraphEngine(strict_validation=False)
    graph_result = graph_engine.analyze(valid_txs)
    graph_summary = graph_result.get("graph_summary", {})
    patterns = graph_result.get("patterns", {})

    # Extract account pattern mapping
    # account_id -> list of pattern names
    account_patterns: Dict[str, List[str]] = {}
    pattern_detail_map: Dict[str, Dict[str, Any]] = {}

    for p_name, p_data in patterns.items():
        for acc in p_data.get("flagged_accounts", []):
            if acc not in account_patterns:
                account_patterns[acc] = []
            account_patterns[acc].append(p_name)

        # Map detail for rapid movement
        if p_name == "rapid_movement":
            for d in p_data.get("details", []):
                acc = d.get("intermediary_account")
                if acc:
                    pattern_detail_map[acc] = {"rapid_movement": d}

    # 3. Feature Extraction
    tx_features_df = extract_transaction_features(valid_txs)
    graph_features_dict = graph_result.get("account_features", {})
    graph_features_df = pd.DataFrame.from_dict(graph_features_dict, orient="index")

    combined_features_df = build_ml_feature_vector(tx_features_df, graph_features_df)

    if combined_features_df.empty:
        return {
            "pipeline_status": "FAILED",
            "error": "Failed to extract feature vectors.",
            "accounts": [],
        }

    # 4. ML Model Fitting & Scoring
    detector = AnomalyDetector(contamination=contamination, random_state=random_state)
    detector.fit(combined_features_df)
    ml_scores_df = detector.compute_anomaly_scores(combined_features_df)

    # 5. Composite Explainable Risk Scoring (Population-Calibrated)
    scorer = ExplainableRiskScorer(feature_df=combined_features_df)
    account_reports: List[Dict[str, Any]] = []
    risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    for acc_id in combined_features_df.index:
        feature_row = combined_features_df.loc[acc_id].to_dict()
        ml_score = float(ml_scores_df.loc[acc_id, "ml_anomaly_score"])
        is_anomaly = bool(ml_scores_df.loc[acc_id, "is_anomaly"])

        active_pats = account_patterns.get(acc_id, [])
        pat_flags = {p: True for p in active_pats}

        final_score, risk_tier, breakdown = scorer.compute_composite_risk(
            account_id=acc_id,
            ml_score=ml_score,
            is_ml_anomaly=is_anomaly,
            feature_row=feature_row,
            pattern_flags=pat_flags,
        )

        risk_dist[risk_tier] = risk_dist.get(risk_tier, 0) + 1

        # Evidence generation
        evidence_list = generate_account_evidence(
            account_id=acc_id,
            features=feature_row,
            active_patterns=active_pats,
            is_ml_anomaly=is_anomaly,
            ml_score=ml_score,
            pattern_details=pattern_detail_map.get(acc_id, {}),
        )

        # Slice relevant sub-features for the contract
        graph_feats = {
            k: feature_row[k]
            for k in [
                "in_degree",
                "out_degree",
                "total_degree",
                "weighted_in_degree",
                "weighted_out_degree",
                "fan_in_score",
                "fan_out_score",
                "cycle_detected",
                "cycle_count",
                "chain_length",
                "network_size",
                "suspicious_neighbor_count",
            ]
            if k in feature_row
        }

        ml_feats = {
            k: feature_row[k]
            for k in [
                "transaction_count",
                "total_incoming",
                "total_outgoing",
                "net_flow",
                "average_transaction_amount",
                "maximum_transaction_amount",
                "transaction_velocity",
                "incoming_outgoing_ratio",
                "counterparty_diversity",
                "passthrough_ratio",
                "amount_volatility",
                "flow_imbalance_magnitude",
            ]
            if k in feature_row
        }


        account_reports.append(
            {
                "account_id": acc_id,
                "risk_score": final_score,
                "risk_level": risk_tier,
                "is_anomaly": is_anomaly,
                "patterns": active_pats,
                "scoring_breakdown": breakdown,
                "evidence": evidence_list,
                "graph_features": graph_feats,
                "ml_features": ml_feats,
            }
        )

    # Sort accounts by risk score descending
    account_reports.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "pipeline_status": "SUCCESS",
        "total_accounts_analyzed": len(account_reports),
        "validation_summary": {
            "is_valid": val_res.is_valid,
            "valid_count": val_res.valid_count,
            "invalid_count": val_res.invalid_count,
            "error_sample": val_res.errors[:5],
        },
        "graph_summary": graph_summary,
        "risk_distribution": risk_dist,
        "accounts": account_reports,
    }


def main() -> None:
    sample_file = os.path.join(PROJECT_ROOT, "data", "synthetic", "transactions_sample.json")
    if not os.path.exists(sample_file):
        print(f"Sample file {sample_file} not found.")
        return

    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = run_pipeline(data)
    print("=== PIPELINE EXECUTION COMPLETED ===")
    print(f"Status: {result['pipeline_status']}")
    print(f"Analyzed {result['total_accounts_analyzed']} accounts.")
    print("Risk Distribution:", result["risk_distribution"])
    print("\nTop 5 Highest Risk Accounts:")
    for acc in result["accounts"][:5]:
        print(f" - [{acc['risk_level']}] {acc['account_id']}: Risk={acc['risk_score']} (Anomaly={acc['is_anomaly']})")
        print(f"   Patterns: {acc['patterns']}")
        print(f"   Evidence: {acc['evidence'][:2]}")


if __name__ == "__main__":
    main()
