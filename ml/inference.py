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
from ml.investigator import build_investigation
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
        c_info = pattern_details.get("circular_flow", {})
        if c_info.get("loop_duration_seconds") is not None:
            evidence.append(
                f"Circular flow pattern detected: funds travelled a {c_info.get('length')}-account loop "
                f"({' -> '.join(c_info.get('cycle_path', []))}) and returned in "
                f"{round(c_info['loop_duration_seconds'] / 60)} minutes with "
                f"{round(c_info.get('amount_retained_ratio', 0) * 100)}% of the value."
            )
        else:
            evidence.append(
                f"Circular flow pattern detected: account participates in {c_count} directed cycle(s)."
            )

    if "rapid_movement" in active_patterns:
        # Check details for fastest latency
        rapid_info = pattern_details.get("rapid_movement", {})
        latency = rapid_info.get("fastest_latency_seconds")
        if latency is not None:
            when = "under a minute" if latency < 60 else f"{round(latency / 60)} minutes"
            evidence.append(
                f"Rapid fund movement detected: funds forwarded within {when} of receipt."
            )
        else:
            evidence.append("Rapid fund movement detected: funds forwarded shortly after receipt.")

    if "fan_in" in active_patterns:
        in_deg = features.get("in_degree", 0)
        out_deg = features.get("out_degree", 0)
        evidence.append(
            f"Fan-in pattern detected: received funds from {int(in_deg)} distinct senders with only {int(out_deg)} outgoing counterparties."
        )

    if "fan_out" in active_patterns:
        in_deg = features.get("in_degree", 0)
        out_deg = features.get("out_degree", 0)
        evidence.append(
            f"Fan-out pattern detected: dispersed funds to {int(out_deg)} distinct receivers from {int(in_deg)} incoming source(s)."
        )

    if "structuring" in active_patterns:
        s_info = pattern_details.get("structuring", {})
        count = s_info.get("near_threshold_count")
        threshold = s_info.get("reporting_threshold")
        if count and threshold:
            verb = "sent" if s_info.get("role") == "splitter" else "received"
            evidence.append(
                f"Structuring detected: {verb} {count} transactions just under the {threshold:,.0f} threshold "
                f"(total {s_info.get('total_amount', 0):,.0f}) within 24 hours."
            )
        else:
            evidence.append("Structuring detected: repeated transactions kept just under the monitoring threshold.")

    if "location_anomaly" in active_patterns:
        d = pattern_details.get("location_anomaly", {})
        usual = ", ".join(d.get("usual_areas", [])) or "elsewhere"
        evidence.append(
            f"Possible account takeover: the wallet normally transacts from {usual} but suddenly moved "
            f"BDT {d.get('outflow_24h', 0):,.0f} in 24 hours from risk area {d.get('risk_area')} "
            f"({'; '.join(d.get('signals', [])[1:]) or 'unusual for this customer'}). Protective alert: confirm with the customer."
        )
    if "takeover_collector" in active_patterns:
        d = pattern_details.get("takeover_collector", {})
        evidence.append(
            f"Takeover collector: received BDT {d.get('amount_collected', 0):,.0f} from {d.get('victim_count')} wallets "
            f"during suspected account takeovers in {', '.join(d.get('risk_areas', []))}."
        )
    if "hundi_operator" in active_patterns:
        d = pattern_details.get("hundi_operator", {})
        evidence.append(
            f"Hundi-style payout: {d.get('informal_inflow_count')} large informal transfers (BDT {d.get('informal_inflow_total', 0):,.0f}) "
            f"from {len(d.get('funders', []))} funder(s) were paid out to {d.get('beneficiary_count')} beneficiaries over {d.get('cycles')} cycles; "
            f"{round(100 * d.get('repeat_beneficiary_share', 0))}% of beneficiaries were paid in more than one cycle. "
            f"No licensed inward-remittance or distributor funding is involved."
        )
    if "hundi_funder" in active_patterns:
        d = pattern_details.get("hundi_funder", {})
        evidence.append(
            f"Hundi funder: sent {d.get('transfers')} large transfers (BDT {d.get('amount', 0):,.0f}) to suspected hundi operator {d.get('operator')}."
        )

    if "coordinated_network" in active_patterns:
        evidence.append(
            "Coordinated network membership: account is part of a densely interconnected transaction cluster."
        )

    chain_len = features.get("chain_length", 0)
    if chain_len >= 3:
        evidence.append(
            f"Transaction chain detected: participates in a multi-hop path spanning {int(chain_len)} hops."
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
            f"High network exposure: directly connected to {int(suspicious_neighbors)} accounts with flagged patterns."
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
    temporal: Optional[bool] = None,
    use_supervised: bool = True,
    account_tiers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Complete execution pipeline returning the structured contract for Member 1.

    temporal picks how circular flows and chains are found: None = by graph size,
    False = exhaustive search on the static graph, True = time-ordered flow tracing.

    use_supervised adds the trained classifier (ml.supervised): the ML component of the score
    becomes the stronger of the IsolationForest anomaly score and the classifier's probability.
    account_tiers maps account_id -> personal | agent | merchant (KYC account type).

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
    graph_engine = GraphEngine(strict_validation=False, temporal=temporal)
    graph_result = graph_engine.analyze(valid_txs)
    graph_summary = graph_result.get("graph_summary", {})
    patterns = graph_result.get("patterns", {})

    # 2b. Context detectors on the transaction stream (risk-area takeover, hundi networks)
    from data.synthetic.profiles import infer_tier
    from ml.context_risk import run_context_detectors

    all_accounts = {tx["sender_id"] for tx in valid_txs} | {tx["receiver_id"] for tx in valid_txs}
    tiers = account_tiers or {str(acc): infer_tier(str(acc)) for acc in all_accounts}
    patterns = {**patterns, **run_context_detectors(valid_txs, tiers)}

    # Extract account pattern mapping
    # account_id -> list of pattern names
    account_patterns: Dict[str, List[str]] = {}
    pattern_detail_map: Dict[str, Dict[str, Any]] = {}

    for p_name, p_data in patterns.items():
        for acc in p_data.get("flagged_accounts", []):
            if acc not in account_patterns:
                account_patterns[acc] = []
            account_patterns[acc].append(p_name)

        # Keep each account's own detail record per pattern for evidence and the investigator
        for d in p_data.get("details", []):
            if p_name in ("circular_flow", "transaction_chain", "coordinated_network"):
                members = d.get("nodes") or d.get("chain_path") or d.get("accounts") or []
            else:
                members = [d.get("account_id") or d.get("intermediary_account")]
            for acc in members:
                if acc and p_name not in pattern_detail_map.setdefault(acc, {}):
                    pattern_detail_map[acc][p_name] = d

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

    # 4b. Supervised classifier trained on the labelled synthetic MFS networks. Optional: if the
    # model cannot be loaded the pipeline falls back to the unsupervised score alone.
    supervised_probs: Dict[str, float] = {}
    supervised_drivers: Dict[str, List[Dict[str, Any]]] = {}
    supervised_threshold: Optional[float] = None
    if use_supervised:
        try:
            from ml.feature_store import build_account_features
            from ml.supervised import explain_accounts, load_or_train, score_accounts

            bundle = load_or_train()
            store = build_account_features(valid_txs, tiers)
            probs = score_accounts(store, bundle)
            supervised_probs = {str(k): float(v) for k, v in probs.items()}
            supervised_threshold = float(bundle["threshold"])
            flagged = [acc for acc, p in supervised_probs.items() if p >= supervised_threshold]
            supervised_drivers = explain_accounts(store, flagged[:500], bundle)
        except Exception as exc:  # pragma: no cover - defensive: scoring must never take the API down
            print(f"[Cygnus ML] supervised model unavailable, using unsupervised score only: {exc}", file=sys.stderr)

    # 5. Composite Explainable Risk Scoring (Population-Calibrated)
    scorer = ExplainableRiskScorer(feature_df=combined_features_df)
    account_reports: List[Dict[str, Any]] = []
    risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    for acc_id in combined_features_df.index:
        feature_row = combined_features_df.loc[acc_id].to_dict()
        anomaly_score = float(ml_scores_df.loc[acc_id, "ml_anomaly_score"])
        is_anomaly = bool(ml_scores_df.loc[acc_id, "is_anomaly"])
        supervised_prob = supervised_probs.get(str(acc_id))
        account_tier = tiers.get(str(acc_id), "personal")
        # ML component: the stronger of "unusual" (IsolationForest) and "looks like a known typology"
        # (classifier). Agents and merchants are statistical outliers by nature of their volume, so for
        # those tiers only the classifier counts once it is available.
        if supervised_prob is None:
            ml_score = anomaly_score
        elif account_tier in ExplainableRiskScorer.BUSINESS_TIERS:
            ml_score = round(100.0 * supervised_prob, 2)
        else:
            ml_score = max(anomaly_score, round(100.0 * supervised_prob, 2))

        active_pats = account_patterns.get(acc_id, [])
        pat_flags = {p: True for p in active_pats}

        final_score, risk_tier, breakdown = scorer.compute_composite_risk(
            account_id=acc_id,
            ml_score=ml_score,
            is_ml_anomaly=is_anomaly,
            feature_row=feature_row,
            pattern_flags=pat_flags,
            account_tier=account_tier if use_supervised else "personal",
        )

        risk_dist[risk_tier] = risk_dist.get(risk_tier, 0) + 1
        breakdown["anomaly_score"] = round(anomaly_score, 2)
        if supervised_prob is not None:
            breakdown["supervised_probability"] = round(supervised_prob, 4)

        # Evidence generation
        evidence_list = generate_account_evidence(
            account_id=acc_id,
            features=feature_row,
            active_patterns=active_pats,
            is_ml_anomaly=is_anomaly,
            ml_score=ml_score,
            pattern_details=pattern_detail_map.get(acc_id, {}),
        )
        drivers = supervised_drivers.get(str(acc_id), [])
        if supervised_prob is not None and supervised_threshold is not None and supervised_prob >= supervised_threshold:
            why = "; ".join(f"{d['label']} = {d['value']:g} (typical {d['typical']:g})" for d in drivers)
            sentence = f"Trained classifier rates this account {supervised_prob * 100:.0f}% similar to known laundering typologies"
            evidence_list.insert(0, f"{sentence}. Main drivers: {why}." if why else f"{sentence}.")
            if evidence_list[-1].startswith("Normal transactional behavior"):
                evidence_list.pop()

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
                "structuring_detected",
                "near_threshold_tx_count",
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


        report = {
            "account_id": acc_id,
            "risk_score": final_score,
            "risk_level": risk_tier,
            "is_anomaly": is_anomaly,
            "patterns": active_pats,
            "scoring_breakdown": breakdown,
            "evidence": evidence_list,
            "graph_features": graph_feats,
            "ml_features": ml_feats,
            "account_tier": account_tier,
            "supervised_probability": None if supervised_prob is None else round(supervised_prob, 4),
            "model_drivers": drivers,
        }
        report["investigation"] = build_investigation(
            report, feature_row, pattern_detail_map.get(acc_id, {})
        )
        account_reports.append(report)

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
        "models": {
            "anomaly": "IsolationForest (unsupervised)",
            "supervised": "Gradient boosting on graph + temporal features" if supervised_probs else None,
            "supervised_threshold": supervised_threshold,
            "detection_mode": graph_result.get("detection_mode"),
        },
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
