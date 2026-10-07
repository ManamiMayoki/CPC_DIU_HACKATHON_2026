"""Cygnus AI - Member 1 Integration Engine Adapter.

Integrates with Member 2 (GraphEngine) and Member 3 (ML Anomaly & Risk Inference)
without modifying any core algorithms or validation rules.
Produces structured data consumed by the Express backend and React UI.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union

import networkx as nx

# Set up system paths to import ml and graph-engine
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
ML_DIR = os.path.join(PROJECT_ROOT, "ml")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")

for path in (PROJECT_ROOT, GRAPH_DIR, ML_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from ml.inference import run_pipeline
from ml.validation import validate_transactions
from graph import build_transaction_graph, get_graph_summary
from data.synthetic.generator import SyntheticDataGenerator


DEFAULT_SAMPLE_PATH = os.path.join(DATA_DIR, "transactions_sample.json")


def load_sample_transactions() -> List[Dict[str, Any]]:
    """Loads default synthetic transactions sample."""
    if os.path.exists(DEFAULT_SAMPLE_PATH):
        with open(DEFAULT_SAMPLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback to generator if file missing
    generator = SyntheticDataGenerator(seed=42)
    return generator.generate_comprehensive_dataset()


def get_demo_scenarios_metadata() -> List[Dict[str, Any]]:
    """Metadata describing each controlled hackathon demo scenario."""
    return [
        {
            "id": "NORMAL",
            "name": "Normal Baseline Peer-to-Peer",
            "target_account": "ACC_NORM_004",
            "expected_pattern": "normal",
            "severity": "LOW",
            "badge_color": "emerald",
            "description": "Standard distributed retail and peer-to-peer transfers with natural time spacing and balanced amounts.",
            "benchmark_note": "False-Positive Rate <= 15.0% verified in benchmark."
        },
        {
            "id": "FAN_IN",
            "name": "Fan-In Aggregation Hub",
            "target_account": "ACC_FANIN_HUB",
            "expected_pattern": "fan_in",
            "severity": "MEDIUM",
            "badge_color": "amber",
            "description": "7+ distinct accounts funneling funds to a single collector account within brief intervals.",
            "benchmark_note": "Target account risk score >= 40.0 with high in-degree ratio."
        },
        {
            "id": "FAN_OUT",
            "name": "Fan-Out Dispersion Hub",
            "target_account": "ACC_FANOUT_HUB",
            "expected_pattern": "fan_out",
            "severity": "MEDIUM",
            "badge_color": "amber",
            "description": "Single primary source dispersing high volumes across multiple receiver accounts.",
            "benchmark_note": "Target account risk score >= 40.0 with high out-degree ratio."
        },
        {
            "id": "RAPID_MOVEMENT",
            "name": "Rapid Passthrough Movement",
            "target_account": "ACC_RAPID_MID",
            "expected_pattern": "rapid_movement",
            "severity": "HIGH",
            "badge_color": "rose",
            "description": "Immediate forwarding (95% of incoming funds forwarded within 5 minutes).",
            "benchmark_note": "Fastest latency: ~300 seconds; high passthrough ratio."
        },
        {
            "id": "CHAIN",
            "name": "Multi-Hop Transaction Chain",
            "target_account": "ACC_CHAIN_02",
            "expected_pattern": "transaction_chain",
            "severity": "MEDIUM",
            "badge_color": "purple",
            "description": "Sequential linear chain across 5 connected accounts (A -> B -> C -> D -> E).",
            "benchmark_note": "Chain length 4+ verified with fee deduction pattern."
        },
        {
            "id": "CIRCULAR_FLOW",
            "name": "Circular Layering Loop",
            "target_account": "ACC_CYCLE_B",
            "expected_pattern": "circular_flow",
            "severity": "HIGH",
            "badge_color": "rose",
            "description": "Closed directed cycle (A -> B -> C -> A) returning funds to originating entity.",
            "benchmark_note": "Cycle participation confirmed by Tarjan/Johnson cycle detection."
        },
        {
            "id": "COORDINATED_NETWORK",
            "name": "Coordinated Account Cluster",
            "target_account": "ACC_COORD_00",
            "expected_pattern": "coordinated_network",
            "severity": "CRITICAL",
            "badge_color": "red",
            "description": "Dense interconnected group of accounts transacting heavily among themselves.",
            "benchmark_note": "Strongly connected component with high internal density."
        },
        {
            "id": "STRUCTURING",
            "name": "Structured Transfers",
            "target_account": "ACC_STRUCT_SRC",
            "expected_pattern": "structuring",
            "severity": "MEDIUM",
            "badge_color": "amber",
            "description": "Five transfers of 9,400-9,950 within a few hours, each kept just under the 10,000 threshold.",
            "benchmark_note": "3+ near-threshold transfers inside 24 hours flag both splitter and collector."
        },
        {
            "id": "MULE_RING",
            "name": "Mule-Ring (MFS Money-Mule Network)",
            "target_account": "ACC_MULE_HUB",
            "expected_pattern": "structuring",
            "severity": "CRITICAL",
            "badge_color": "red",
            "description": "8 feeder wallets -> collector hub -> 4 mule wallets -> cash-out agent -> back to the hub, all within about two hours.",
            "benchmark_note": "Fan-in, structuring, rapid movement, chain and a time-ordered loop combine into a CRITICAL score."
        },
    ]


def build_enhanced_payload(
    transactions: List[Dict[str, Any]],
    pipeline_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Combines Member 2 graph topology + Member 3 ML inference into a rich product response."""
    accounts_list = pipeline_result.get("accounts", [])
    account_map = {acc["account_id"]: acc for acc in accounts_list}

    # Build NetworkX graph for edge aggregation & topology
    # (callers pass the validated transactions, so rejected records never reach the UI graph)
    graph = build_transaction_graph(transactions, multi_graph=False)
    summary = get_graph_summary(graph)

    # Collect pattern sets per account
    account_patterns_map = {acc["account_id"]: acc.get("patterns", []) for acc in accounts_list}
    account_risk_map = {acc["account_id"]: acc.get("risk_score", 0.0) for acc in accounts_list}
    account_tier_map = {acc["account_id"]: acc.get("risk_level", "LOW") for acc in accounts_list}

    # Format nodes
    nodes: List[Dict[str, Any]] = []
    for node_id in graph.nodes():
        acc_info = account_map.get(node_id, {})
        patterns = acc_info.get("patterns", [])
        risk_score = acc_info.get("risk_score", 15.0)
        risk_level = acc_info.get("risk_level", "LOW")
        is_anomaly = acc_info.get("is_anomaly", False)
        ml_features = acc_info.get("ml_features", {})
        graph_features = acc_info.get("graph_features", {})

        in_weight = float(graph_features.get("weighted_in_degree", 0.0))
        out_weight = float(graph_features.get("weighted_out_degree", 0.0))
        tx_count = int(ml_features.get("transaction_count", graph.degree(node_id)))

        nodes.append({
            "id": str(node_id),
            "label": str(node_id),
            "risk_score": round(risk_score, 2),
            "risk_level": risk_level,
            "is_anomaly": is_anomaly,
            "patterns": patterns,
            "has_patterns": len(patterns) > 0,
            "in_degree": int(graph.in_degree(node_id)),
            "out_degree": int(graph.out_degree(node_id)),
            "total_degree": int(graph.degree(node_id)),
            "incoming_amount": round(in_weight, 2),
            "outgoing_amount": round(out_weight, 2),
            "net_flow": round(in_weight - out_weight, 2),
            "transaction_count": tx_count,
            "evidence": acc_info.get("evidence", []),
            "investigation": acc_info.get("investigation"),
            "scoring_breakdown": acc_info.get("scoring_breakdown", {
                "ml_component": 20.0,
                "graph_component": 15.0,
                "behavioral_component": 10.0,
            }),
            "ml_features": ml_features,
            "graph_features": graph_features,
        })

    # Format edges
    edges: List[Dict[str, Any]] = []
    edge_idx = 0
    for u, v, data in graph.edges(data=True):
        edge_idx += 1
        weight = float(data.get("weight", 0.0))
        count = int(data.get("count", 1))
        latest_ts = str(data.get("timestamp", ""))
        tx_id = str(data.get("transaction_id", f"E_{edge_idx}"))
        tx_list = data.get("transactions", [])

        # Check if edge connects suspicious accounts or is part of a flagged pattern
        u_patterns = account_patterns_map.get(u, [])
        v_patterns = account_patterns_map.get(v, [])
        shared_patterns = sorted(set(u_patterns) & set(v_patterns))
        
        u_tier = account_tier_map.get(u, "LOW")
        v_tier = account_tier_map.get(v, "LOW")
        is_suspicious = (
            len(shared_patterns) > 0
            or u_tier in ("HIGH", "CRITICAL")
            or v_tier in ("HIGH", "CRITICAL")
            or (u_tier == "MEDIUM" and v_tier == "MEDIUM")
        )

        edges.append({
            "id": f"e_{u}_{v}",
            "source": str(u),
            "target": str(v),
            "amount": round(weight, 2),
            "count": count,
            "timestamp": latest_ts,
            "transaction_id": tx_id,
            "is_suspicious": is_suspicious,
            "shared_patterns": shared_patterns,
            "transactions": tx_list,
        })

    # Pattern definitions and status
    pattern_catalog = [
        {
            "id": "fan_in",
            "name": "Fan-In Aggregation",
            "title": "Fan-In Hub",
            "description": "Multiple distinct accounts channeling money rapidly into a single central hub.",
            "severity": "HIGH",
            "badge_color": "amber",
        },
        {
            "id": "fan_out",
            "name": "Fan-Out Dispersion",
            "title": "Fan-Out Hub",
            "description": "A single distributor funneling money outward to multiple separate beneficiary accounts.",
            "severity": "HIGH",
            "badge_color": "amber",
        },
        {
            "id": "rapid_movement",
            "name": "Rapid Movement",
            "title": "Rapid Passthrough",
            "description": "Incoming funds of 1,000+ forwarded onward within an hour, keeping 70-110% of the amount.",
            "severity": "CRITICAL",
            "badge_color": "rose",
        },
        {
            "id": "transaction_chain",
            "name": "Transaction Chain",
            "title": "Multi-Hop Chain",
            "description": "Linear layering sequences spanning 3+ consecutive accounts with minimal balance retention.",
            "severity": "MEDIUM",
            "badge_color": "purple",
        },
        {
            "id": "circular_flow",
            "name": "Circular Flow",
            "title": "Circular Loop",
            "description": "Money that travels a closed loop (A -> B -> C -> A) in time order within 6 hours and returns to its origin.",
            "severity": "CRITICAL",
            "badge_color": "red",
        },
        {
            "id": "structuring",
            "name": "Structuring",
            "title": "Structured Transfers",
            "description": "Several transactions kept just under the 10,000 threshold within 24 hours to avoid monitoring.",
            "severity": "HIGH",
            "badge_color": "amber",
        },
        {
            "id": "coordinated_network",
            "name": "Coordinated Network",
            "title": "Coordinated Cluster",
            "description": "Densely interconnected clusters with high mutual transaction density.",
            "severity": "CRITICAL",
            "badge_color": "red",
        },
    ]

    patterns_summary = []
    for pat in pattern_catalog:
        pid = pat["id"]
        flagged = [acc["account_id"] for acc in accounts_list if pid in acc.get("patterns", [])]
        patterns_summary.append({
            "id": pid,
            "name": pat["name"],
            "title": pat["title"],
            "status": "Detected" if len(flagged) > 0 else "Clean",
            "detected": len(flagged) > 0,
            "severity": pat["severity"],
            "badge_color": pat["badge_color"],
            "description": pat["description"],
            "affected_accounts_count": len(flagged),
            "flagged_accounts": flagged,
        })

    # Global Stats
    total_tx = len(transactions)
    total_acc = len(nodes)
    high_risk_accs = sum(1 for a in accounts_list if a.get("risk_level") in ("HIGH", "CRITICAL"))
    med_risk_accs = sum(1 for a in accounts_list if a.get("risk_level") == "MEDIUM")
    avg_risk = round(sum(a.get("risk_score", 0.0) for a in accounts_list) / max(1, len(accounts_list)), 1)
    # Every account outside a cycle is its own single-node SCC, so only multi-account SCCs count here
    multi_account_sccs = sum(1 for comp in nx.strongly_connected_components(graph) if len(comp) > 1)
    suspicious_networks_count = multi_account_sccs + sum(
        1 for p in patterns_summary if p["detected"]
    )

    stats = {
        "total_transactions": total_tx,
        "total_accounts": total_acc,
        "suspicious_networks": suspicious_networks_count,
        "high_risk_accounts": high_risk_accs,
        "medium_risk_accounts": med_risk_accs,
        "active_detection_patterns": sum(1 for p in patterns_summary if p["detected"]),
        "average_risk_score": avg_risk,
        "graph_density": summary.get("density", 0.0),
        "weakly_connected_components": summary.get("weakly_connected_components", 0),
        "strongly_connected_components": summary.get("strongly_connected_components", 0),
    }

    # Analytics aggregations
    # 1. Volume over time
    tx_by_hour: Dict[str, Dict[str, float]] = {}
    for tx in transactions:
        ts = str(tx.get("timestamp", ""))
        amount = float(tx.get("amount", 0.0))
        hour_key = ts[:13] if len(ts) >= 13 else "2026-03-01T10"
        if hour_key not in tx_by_hour:
            tx_by_hour[hour_key] = {"time": hour_key.replace("T", " "), "volume": 0.0, "count": 0}
        tx_by_hour[hour_key]["volume"] = round(tx_by_hour[hour_key]["volume"] + amount, 2)
        tx_by_hour[hour_key]["count"] += 1

    volume_timeline = sorted(tx_by_hour.values(), key=lambda x: x["time"])

    # 2. Risk distribution
    risk_distribution = pipeline_result.get("risk_distribution", {
        "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0
    })

    # 3. Pattern frequency
    pattern_freq = [
        {"pattern": p["title"], "count": p["affected_accounts_count"], "severity": p["severity"]}
        for p in patterns_summary
    ]

    # 4. Top high risk accounts
    top_risk_accounts = [
        {
            "account_id": a["account_id"],
            "risk_score": a["risk_score"],
            "risk_level": a["risk_level"],
            "is_anomaly": a["is_anomaly"],
            "patterns": a.get("patterns", []),
            "evidence": a.get("evidence", []),
            "investigation": a.get("investigation"),
            "transactions_count": a.get("ml_features", {}).get("transaction_count", 0),
            "incoming": a.get("ml_features", {}).get("total_incoming", 0.0),
            "outgoing": a.get("ml_features", {}).get("total_outgoing", 0.0),
            "scoring_breakdown": a.get("scoring_breakdown", {}),
        }
        for a in accounts_list[:15]
    ]

    # Show each demo scenario's badge at the tier the pipeline actually assigned its target account
    demo_scenarios = []
    for scenario in get_demo_scenarios_metadata():
        target_tier = account_tier_map.get(scenario["target_account"])
        demo_scenarios.append({**scenario, "severity": target_tier or scenario["severity"]})

    return {
        "status": "SUCCESS",
        "pipeline_status": pipeline_result.get("pipeline_status", "SUCCESS"),
        "total_accounts_analyzed": len(accounts_list),
        "validation_summary": pipeline_result.get("validation_summary", {}),
        "graph_summary": summary,
        "stats": stats,
        "nodes": nodes,
        "edges": edges,
        "accounts": accounts_list,
        "top_risk_accounts": top_risk_accounts,
        "patterns_summary": patterns_summary,
        "risk_distribution": risk_distribution,
        "demo_scenarios": demo_scenarios,
        "analytics": {
            "volume_timeline": volume_timeline,
            "risk_distribution": risk_distribution,
            "pattern_frequency": pattern_freq,
        },
        "transactions_sample": transactions[:100],  # first 100 for table preview
        "total_transactions_count": len(transactions),
    }


def analyze_dataset(transactions: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Runs full pipeline and returns enhanced payload."""
    if transactions is None:
        transactions = load_sample_transactions()

    pipeline_result = run_pipeline(
        transactions=transactions,
        contamination=0.10,
        random_state=42,
        strict_validation=False,
    )

    valid_transactions = validate_transactions(transactions, strict=False).valid_transactions
    return build_enhanced_payload(valid_transactions, pipeline_result)


def get_account_subgraph(
    account_id: str,
    transactions: Optional[List[Dict[str, Any]]] = None,
    hops: int = 1,
) -> Dict[str, Any]:
    """Extracts 1-hop or 2-hop ego network for 'Follow the Money' visualization."""
    if transactions is None:
        transactions = load_sample_transactions()

    full_payload = analyze_dataset(transactions)
    nodes = full_payload["nodes"]
    edges = full_payload["edges"]
    node_map = {n["id"]: n for n in nodes}

    target_id = str(account_id).strip()
    if target_id not in node_map:
        return {
            "success": False,
            "error": f"Account '{target_id}' not found in transaction dataset.",
            "target_id": target_id,
            "nodes": [],
            "edges": [],
        }

    # Find connected neighbors
    visited_nodes = {target_id}
    current_frontier = {target_id}

    for _ in range(hops):
        next_frontier = set()
        for e in edges:
            if e["source"] in current_frontier:
                next_frontier.add(e["target"])
            if e["target"] in current_frontier:
                next_frontier.add(e["source"])
        visited_nodes.update(next_frontier)
        current_frontier = next_frontier

    subgraph_nodes = []
    for nid in visited_nodes:
        if nid in node_map:
            n_data = dict(node_map[nid])
            n_data["is_target"] = (nid == target_id)
            subgraph_nodes.append(n_data)

    subgraph_edges = [
        e for e in edges
        if e["source"] in visited_nodes and e["target"] in visited_nodes
    ]

    target_node = node_map[target_id]
    target_evidence = target_node.get("evidence", [])
    target_breakdown = target_node.get("scoring_breakdown", {})

    return {
        "success": True,
        "target_account": target_node,
        "target_id": target_id,
        "hops": hops,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges,
        "node_count": len(subgraph_nodes),
        "edge_count": len(subgraph_edges),
        "evidence": target_evidence,
        "investigation": target_node.get("investigation"),
        "scoring_breakdown": target_breakdown,
        "patterns": target_node.get("patterns", []),
        "risk_score": target_node.get("risk_score", 0.0),
        "risk_level": target_node.get("risk_level", "LOW"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Cygnus AI Integration Adapter")
    parser.add_argument("--action", choices=["analyze", "account", "scenarios", "summary"], default="analyze")
    parser.add_argument("--account", type=str, help="Target account ID")
    parser.add_argument("--hops", type=int, default=1, help="Ego network hops")
    parser.add_argument("--out", type=str, help="Output JSON path")
    parser.add_argument("--input", type=str, help="Transactions JSON file to analyze (defaults to the synthetic sample)")
    args = parser.parse_args()

    transactions = None
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            transactions = json.load(f)

    if args.action == "scenarios":
        output = {"scenarios": get_demo_scenarios_metadata()}
    elif args.action == "account" and args.account:
        output = get_account_subgraph(args.account, transactions=transactions, hops=args.hops)
    elif args.action == "summary":
        full = analyze_dataset(transactions)
        output = {
            "stats": full["stats"],
            "risk_distribution": full["risk_distribution"],
            "patterns_summary": full["patterns_summary"],
        }
    else:
        output = analyze_dataset(transactions)

    json_str = json.dumps(output, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Output saved to {args.out}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
