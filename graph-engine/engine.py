"""Graph Analysis Engine.

Orchestrates graph building, suspicious network pattern detection, and topological
feature extraction for Member 1 backend integration and Member 3 ML pipelines.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Union
import pandas as pd

# Support running directly or as imported module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR in sys.path:
    sys.path.remove(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from graph import build_transaction_graph, get_graph_summary
from patterns import run_all_network_detections, PatternDetectionResult, TEMPORAL_MODE_NODE_LIMIT
from features import extract_graph_features
from ml.validation import validate_transactions, ValidationResult



class GraphEngine:
    """Core analysis engine for transaction graphs and topological pattern discovery."""

    def __init__(self, strict_validation: bool = False, temporal: Optional[bool] = None) -> None:
        self.strict_validation = strict_validation
        # None = choose by graph size (see patterns.TEMPORAL_MODE_NODE_LIMIT)
        self.temporal = temporal

    def analyze(
        self,
        transactions: Union[List[Dict[str, Any]], pd.DataFrame],
    ) -> Dict[str, Any]:
        """Runs the complete graph analysis workflow.

        Steps:
        1. Validate transactions for integrity.
        2. Build NetworkX directed transaction graph.
        3. Detect all suspicious topology patterns (fan-in, fan-out, circular flows, etc.).
        4. Extract account-level graph features.
        5. Return clean structured dictionary.
        """
        # Step 1: Validation
        val_res: ValidationResult = validate_transactions(
            transactions, strict=self.strict_validation
        )
        if not val_res.valid_transactions:
            return {
                "success": False,
                "error": "No valid transactions to construct graph.",
                "validation": {
                    "is_valid": val_res.is_valid,
                    "errors": val_res.errors,
                    "valid_count": val_res.valid_count,
                    "invalid_count": val_res.invalid_count,
                },
                "graph_summary": {},
                "patterns": {},
                "account_features": {},
            }

        valid_txs = val_res.valid_transactions

        # Step 2: Build graph
        graph = build_transaction_graph(valid_txs)
        summary = get_graph_summary(graph)

        # Step 3: Run pattern detections
        pattern_results: Dict[str, PatternDetectionResult] = run_all_network_detections(graph, temporal=self.temporal)

        # Convert pattern results to JSON-serializable dictionaries
        patterns_dict = {}
        for name, res in pattern_results.items():
            patterns_dict[name] = {
                "detected": res.detected,
                "flagged_accounts": res.flagged_accounts,
                "count": len(res.flagged_accounts),
                "description": res.description,
                "details": res.details,
            }

        # Step 4: Extract graph features
        features_df = extract_graph_features(graph, precomputed_patterns=pattern_results)
        account_features = features_df.to_dict(orient="index") if not features_df.empty else {}

        return {
            "success": True,
            "validation": {
                "is_valid": val_res.is_valid,
                "valid_count": val_res.valid_count,
                "invalid_count": val_res.invalid_count,
                "errors": val_res.errors[:10],
            },
            "graph_summary": summary,
            "patterns": patterns_dict,
            "account_features": account_features,
            "detection_mode": "temporal flow tracing" if (
                self.temporal if self.temporal is not None else graph.number_of_nodes() > TEMPORAL_MODE_NODE_LIMIT
            ) else "exhaustive graph search",
        }


def main() -> None:
    sample_file = os.path.join(PROJECT_ROOT, "data", "synthetic", "transactions_sample.json")
    if not os.path.exists(sample_file):
        print(f"Sample file not found at {sample_file}")
        return

    with open(sample_file, "r", encoding="utf-8") as f:
        transactions = json.load(f)

    engine = GraphEngine()
    result = engine.analyze(transactions)
    print("=== GRAPH ENGINE ANALYSIS SUMMARY ===")
    print("Graph Metrics:", result["graph_summary"])
    print("\nDetected Patterns:")
    for pat, data in result["patterns"].items():
        print(f" - {pat}: detected={data['detected']}, flagged={len(data['flagged_accounts'])} accounts")
    print(f"\nExtracted features for {len(result['account_features'])} accounts.")


if __name__ == "__main__":
    main()
