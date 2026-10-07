"""Account-Level Graph Feature Engineering.

Extracts topological graph features from the transaction network that ML models
can consume. Keeps feature generation completely decoupled from ML models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
import networkx as nx
import pandas as pd

try:
    from patterns import PatternDetectionResult, run_all_network_detections
except ImportError:
    from .patterns import PatternDetectionResult, run_all_network_detections



def extract_graph_features(
    graph: nx.DiGraph,
    precomputed_patterns: Optional[Dict[str, PatternDetectionResult]] = None,
) -> pd.DataFrame:
    """Extracts account-level graph features for all nodes in the transaction graph.

    Features generated per account:
    - in_degree: Number of incoming transaction counterparties
    - out_degree: Number of outgoing transaction counterparties
    - total_degree: Total degree (in_degree + out_degree)
    - degree_ratio: in_degree / (out_degree + 1)
    - weighted_in_degree: Total sum of incoming monetary amounts
    - weighted_out_degree: Total sum of outgoing monetary amounts
    - net_weight_flow: weighted_in_degree - weighted_out_degree
    - unique_counterparties: Count of unique connected counterparties
    - fan_in_score: Heuristic fan-in indicator score [0.0 - 1.0]
    - fan_out_score: Heuristic fan-out indicator score [0.0 - 1.0]
    - cycle_detected: 1 if account belongs to a circular flow cycle, else 0
    - cycle_count: Number of detected cycles node participates in
    - chain_length: Maximum chain length involving this node (or 0)
    - structuring_detected: 1 if account splits or collects near-threshold transactions, else 0
    - near_threshold_tx_count: Near-threshold transactions in the account's busiest structuring window
    - network_size: Size of the weakly connected component containing this node
    - suspicious_neighbor_count: Number of direct 1-hop neighbors flagged in detected patterns

    Returns:
        pd.DataFrame indexed by account_id.
    """
    if graph.number_of_nodes() == 0:
        return pd.DataFrame()

    patterns = precomputed_patterns or run_all_network_detections(graph)

    # Pre-index pattern flags for fast lookup
    fan_in_nodes = set(patterns.get("fan_in", PatternDetectionResult("fan_in", False, [])).flagged_accounts)
    fan_out_nodes = set(patterns.get("fan_out", PatternDetectionResult("fan_out", False, [])).flagged_accounts)
    rapid_nodes = set(patterns.get("rapid_movement", PatternDetectionResult("rapid_movement", False, [])).flagged_accounts)
    coord_nodes = set(patterns.get("coordinated_network", PatternDetectionResult("coordinated_network", False, [])).flagged_accounts)
    structuring_res = patterns.get("structuring", PatternDetectionResult("structuring", False, []))
    structuring_nodes = set(structuring_res.flagged_accounts)
    node_near_threshold: Dict[str, int] = {}
    for detail in structuring_res.details:
        acc = detail.get("account_id")
        node_near_threshold[acc] = max(node_near_threshold.get(acc, 0), int(detail.get("near_threshold_count", 0)))

    # Cycle lookup
    cycle_res = patterns.get("circular_flow")
    cycle_nodes = set(cycle_res.flagged_accounts) if cycle_res else set()
    node_cycle_counts: Dict[str, int] = {}
    if cycle_res:
        for detail in cycle_res.details:
            for n in detail.get("nodes", []):
                node_cycle_counts[n] = node_cycle_counts.get(n, 0) + 1

    # Chain lookup
    chain_res = patterns.get("transaction_chain")
    node_chain_lens: Dict[str, int] = {}
    if chain_res:
        for detail in chain_res.details:
            hops = detail.get("hops", 0)
            for n in detail.get("chain_path", []):
                node_chain_lens[n] = max(node_chain_lens.get(n, 0), hops)
        # Temporal mode reports every account's chain length, not only those in the capped detail list
        for n, hops in getattr(chain_res, "chain_lengths", {}).items():
            node_chain_lens[n] = max(node_chain_lens.get(n, 0), hops)

    # Union of all flagged nodes across any pattern
    all_flagged: Set[str] = fan_in_nodes | fan_out_nodes | rapid_nodes | coord_nodes | cycle_nodes | structuring_nodes

    # Precompute weakly connected component sizes
    wcc_map: Dict[str, int] = {}
    for comp in nx.weakly_connected_components(graph):
        c_size = len(comp)
        for n in comp:
            wcc_map[n] = c_size

    feature_records: List[Dict[str, Any]] = []

    for node in graph.nodes():
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)
        total_deg = in_deg + out_deg

        preds = set(graph.predecessors(node))
        succs = set(graph.successors(node))
        counterparties = len(preds | succs)

        w_in = sum(graph[u][node].get("weight", 0.0) for u in preds)
        w_out = sum(graph[node][v].get("weight", 0.0) for v in succs)

        # Degree ratio
        deg_ratio = float(in_deg) / (out_deg + 1.0)

        # Normalized fan-in / fan-out heuristic scores (0.0 to 1.0)
        fan_in_score = min(1.0, (in_deg / max(1, out_deg * 2)) if in_deg >= 3 else 0.0)
        fan_out_score = min(1.0, (out_deg / max(1, in_deg * 2)) if out_deg >= 3 else 0.0)

        # Suspicious neighbor count
        suspicious_neighbors = sum(1 for neighbor in (preds | succs) if neighbor in all_flagged)

        feature_records.append({
            "account_id": node,
            "in_degree": int(in_deg),
            "out_degree": int(out_deg),
            "total_degree": int(total_deg),
            "degree_ratio": round(deg_ratio, 4),
            "weighted_in_degree": round(w_in, 4),
            "weighted_out_degree": round(w_out, 4),
            "net_weight_flow": round(w_in - w_out, 4),
            "unique_counterparties": int(counterparties),
            "fan_in_score": round(fan_in_score, 4),
            "fan_out_score": round(fan_out_score, 4),
            "cycle_detected": 1 if node in cycle_nodes else 0,
            "cycle_count": int(node_cycle_counts.get(node, 0)),
            "chain_length": int(node_chain_lens.get(node, 0)),
            "structuring_detected": 1 if node in structuring_nodes else 0,
            "near_threshold_tx_count": int(node_near_threshold.get(node, 0)),
            "network_size": int(wcc_map.get(node, 1)),
            "suspicious_neighbor_count": int(suspicious_neighbors),
        })

    df = pd.DataFrame(feature_records)
    if not df.empty:
        df.set_index("account_id", inplace=True)
    return df
