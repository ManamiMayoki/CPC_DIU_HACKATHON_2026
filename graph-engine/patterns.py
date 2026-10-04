"""Suspicious Network Pattern Detection Algorithms.

DISCLAIMER: These detection algorithms identify structural graph anomalies and
suspicious behavioral indicators on synthetic transaction data. They do NOT prove
financial crime, illegal activity, or money laundering. They serve as behavioral
flags for risk assessment and investigation prioritization.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx

from ml.validation import parse_iso_timestamp


@dataclass
class PatternDetectionResult:
    """Standardized result schema for detected network patterns."""
    pattern_name: str
    detected: bool
    flagged_accounts: List[str]
    details: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""


def detect_fan_in(
    graph: nx.DiGraph,
    min_in_degree: int = 4,
    min_in_out_ratio: float = 2.0,
) -> PatternDetectionResult:
    """Detects Fan-In patterns: Multiple accounts funneling money into a single collector account.

    An account is flagged if:
    1. Its in_degree >= min_in_degree, and
    2. Its in_degree to out_degree ratio >= min_in_out_ratio (or out_degree is 0).
    """
    flagged = []
    details = []

    for node in graph.nodes():
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)

        if in_deg >= min_in_degree:
            ratio = float(in_deg) / (out_deg if out_deg > 0 else 0.5)
            if ratio >= min_in_out_ratio:
                senders = list(graph.predecessors(node))
                total_in_weight = sum(
                    graph[u][node].get("weight", 0.0) for u in senders
                )
                flagged.append(node)
                details.append({
                    "account_id": node,
                    "in_degree": in_deg,
                    "out_degree": out_deg,
                    "in_out_ratio": round(ratio, 2),
                    "total_incoming_amount": round(total_in_weight, 2),
                    "senders": senders,
                })

    return PatternDetectionResult(
        pattern_name="fan_in",
        detected=len(flagged) > 0,
        flagged_accounts=flagged,
        details=details,
        description=f"Identified {len(flagged)} collector account(s) receiving funds from {min_in_degree}+ distinct counterparties.",
    )


def detect_fan_out(
    graph: nx.DiGraph,
    min_out_degree: int = 4,
    min_out_in_ratio: float = 2.0,
) -> PatternDetectionResult:
    """Detects Fan-Out patterns: A single account dispersing money to multiple distinct accounts.

    An account is flagged if:
    1. Its out_degree >= min_out_degree, and
    2. Its out_degree to in_degree ratio >= min_out_in_ratio (or in_degree is 0).
    """
    flagged = []
    details = []

    for node in graph.nodes():
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)

        if out_deg >= min_out_degree:
            ratio = float(out_deg) / (in_deg if in_deg > 0 else 0.5)
            if ratio >= min_out_in_ratio:
                receivers = list(graph.successors(node))
                total_out_weight = sum(
                    graph[node][v].get("weight", 0.0) for v in receivers
                )
                flagged.append(node)
                details.append({
                    "account_id": node,
                    "in_degree": in_deg,
                    "out_degree": out_deg,
                    "out_in_ratio": round(ratio, 2),
                    "total_outgoing_amount": round(total_out_weight, 2),
                    "receivers": receivers,
                })

    return PatternDetectionResult(
        pattern_name="fan_out",
        detected=len(flagged) > 0,
        flagged_accounts=flagged,
        details=details,
        description=f"Identified {len(flagged)} distributor account(s) dispersing funds to {min_out_degree}+ distinct counterparties.",
    )


def detect_circular_flows(
    graph: nx.DiGraph,
    min_cycle_length: int = 3,
    max_cycle_length: int = 6,
    max_cycles_to_search: int = 50,
) -> PatternDetectionResult:
    """Detects circular transaction paths (e.g. A -> B -> C -> A).

    Cycles of length >= min_cycle_length are flagged to distinguish genuine layering
    from simple bidirectional reciprocal payments (length 2).
    """
    flagged_set: Set[str] = set()
    details = []

    # To maintain deterministic and efficient runtime on large graphs,
    # find cycles with depth bounded by max_cycle_length
    try:
        cycles_generator = nx.simple_cycles(graph)
        cycle_count = 0
        for cycle in cycles_generator:
            cycle_len = len(cycle)
            if min_cycle_length <= cycle_len <= max_cycle_length:
                flagged_set.update(cycle)
                details.append({
                    "cycle_path": cycle + [cycle[0]],
                    "length": cycle_len,
                    "nodes": cycle,
                })
                cycle_count += 1
                if cycle_count >= max_cycles_to_search:
                    break
    except Exception:
        # Fallback if graph is empty or has issues
        pass

    flagged_list = sorted(list(flagged_set))
    return PatternDetectionResult(
        pattern_name="circular_flow",
        detected=len(flagged_list) > 0,
        flagged_accounts=flagged_list,
        details=details,
        description=f"Detected {len(details)} circular flow cycle(s) involving {len(flagged_list)} account(s).",
    )


def detect_transaction_chains(
    graph: nx.DiGraph,
    min_hops: int = 3,
    max_paths_to_search: int = 50,
) -> PatternDetectionResult:
    """Detects multi-hop transaction chains: A -> B -> C -> D (length >= min_hops).

    Finds directed paths where funds move across a sequence of intermediary accounts.
    """
    flagged_set: Set[str] = set()
    details = []
    path_count = 0

    # Find nodes with in_degree > 0 and out_degree > 0 (intermediaries)
    intermediaries = [n for n in graph.nodes() if graph.in_degree(n) > 0 and graph.out_degree(n) > 0]
    sources = [n for n in graph.nodes() if graph.in_degree(n) == 0 and graph.out_degree(n) > 0]

    # If no pure sources, use nodes with out_degree > in_degree
    search_starts = sources if sources else [n for n in graph.nodes() if graph.out_degree(n) > 0]

    for start_node in search_starts[:20]:
        # DFS to find paths of at least min_hops
        stack: List[Tuple[str, List[str]]] = [(start_node, [start_node])]
        while stack:
            curr, path = stack.pop()
            if len(path) - 1 >= min_hops:
                flagged_set.update(path)
                details.append({
                    "chain_path": path,
                    "hops": len(path) - 1,
                    "start": path[0],
                    "end": path[-1],
                })
                path_count += 1
                if path_count >= max_paths_to_search:
                    break
            if len(path) - 1 < min_hops + 2:
                for succ in graph.successors(curr):
                    if succ not in path:  # avoid cycles here
                        stack.append((succ, path + [succ]))
        if path_count >= max_paths_to_search:
            break

    flagged_list = sorted(list(flagged_set))
    return PatternDetectionResult(
        pattern_name="transaction_chain",
        detected=len(flagged_list) > 0,
        flagged_accounts=flagged_list,
        details=details,
        description=f"Identified {len(details)} multi-hop transaction chain(s) with {min_hops}+ hops across {len(flagged_list)} account(s).",
    )


def detect_rapid_movement(
    graph: nx.DiGraph,
    time_window_seconds: float = 3600.0,  # 1 hour
    amount_tolerance_ratio: float = 0.70,  # Outflow >= 70% of inflow
) -> PatternDetectionResult:
    """Detects rapid fund passthrough: An account receives funds and forwards a comparable amount within a short time window.

    Characteristics:
    - Account B receives money from A at t1
    - Account B sends money to C at t2, where 0 < (t2 - t1) <= time_window_seconds
    - amount(out) >= amount_tolerance_ratio * amount(in)
    """
    flagged_set: Set[str] = set()
    details = []

    for node in graph.nodes():
        # Check if node has both predecessors and successors
        preds = list(graph.predecessors(node))
        succs = list(graph.successors(node))
        if not preds or not succs:
            continue

        # Extract all incoming transactions
        incoming_txs = []
        for u in preds:
            txs = graph[u][node].get("transactions", [])
            for t in txs:
                dt = parse_iso_timestamp(t.get("timestamp"))
                if dt:
                    incoming_txs.append({"source": u, "amount": t.get("amount", 0.0), "dt": dt})

        # Extract all outgoing transactions
        outgoing_txs = []
        for v in succs:
            txs = graph[node][v].get("transactions", [])
            for t in txs:
                dt = parse_iso_timestamp(t.get("timestamp"))
                if dt:
                    outgoing_txs.append({"destination": v, "amount": t.get("amount", 0.0), "dt": dt})

        # Sort chronologically
        incoming_txs.sort(key=lambda x: x["dt"])
        outgoing_txs.sort(key=lambda x: x["dt"])

        # Match incoming and outgoing pairs
        node_rapid_cases = []
        for in_tx in incoming_txs:
            for out_tx in outgoing_txs:
                time_diff = (out_tx["dt"] - in_tx["dt"]).total_seconds()
                if 0 <= time_diff <= time_window_seconds:
                    # Check amount similarity (e.g. forward 70% to 110%)
                    if out_tx["amount"] >= in_tx["amount"] * amount_tolerance_ratio:
                        node_rapid_cases.append({
                            "incoming_from": in_tx["source"],
                            "incoming_amount": in_tx["amount"],
                            "incoming_time": in_tx["dt"].isoformat(),
                            "outgoing_to": out_tx["destination"],
                            "outgoing_amount": out_tx["amount"],
                            "outgoing_time": out_tx["dt"].isoformat(),
                            "latency_seconds": round(time_diff, 1),
                        })

        if node_rapid_cases:
            flagged_set.add(node)
            details.append({
                "intermediary_account": node,
                "matches": node_rapid_cases,
                "fastest_latency_seconds": min(c["latency_seconds"] for c in node_rapid_cases),
            })

    flagged_list = sorted(list(flagged_set))
    return PatternDetectionResult(
        pattern_name="rapid_movement",
        detected=len(flagged_list) > 0,
        flagged_accounts=flagged_list,
        details=details,
        description=f"Identified {len(flagged_list)} intermediary account(s) executing rapid passthrough within {int(time_window_seconds / 60)} minutes.",
    )


def detect_coordinated_networks(
    graph: nx.DiGraph,
    min_cluster_size: int = 3,
    min_internal_density: float = 0.4,
) -> PatternDetectionResult:
    """Identifies coordinated account networks: Subgroups of accounts with unusually high internal interconnectivity.

    Evaluates strongly connected components (SCCs) and dense subgraphs with size >= min_cluster_size.
    """
    flagged_set: Set[str] = set()
    details = []

    # Check strongly connected components
    for scc in nx.strongly_connected_components(graph):
        if len(scc) >= min_cluster_size:
            subg = graph.subgraph(scc)
            internal_density = nx.density(subg)
            if internal_density >= min_internal_density:
                flagged_set.update(scc)
                details.append({
                    "network_type": "strongly_connected_dense_cluster",
                    "accounts": sorted(list(scc)),
                    "size": len(scc),
                    "density": round(internal_density, 3),
                    "edge_count": subg.number_of_edges(),
                })

    flagged_list = sorted(list(flagged_set))
    return PatternDetectionResult(
        pattern_name="coordinated_network",
        detected=len(flagged_list) > 0,
        flagged_accounts=flagged_list,
        details=details,
        description=f"Identified {len(details)} coordinated cluster(s) comprising {len(flagged_list)} densely interconnected accounts.",
    )


def run_all_network_detections(graph: nx.DiGraph) -> Dict[str, PatternDetectionResult]:
    """Executes all pattern detection algorithms against the provided transaction graph."""
    return {
        "fan_in": detect_fan_in(graph),
        "fan_out": detect_fan_out(graph),
        "circular_flow": detect_circular_flows(graph),
        "transaction_chain": detect_transaction_chains(graph),
        "rapid_movement": detect_rapid_movement(graph),
        "coordinated_network": detect_coordinated_networks(graph),
    }
