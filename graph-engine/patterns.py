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


def _max_distinct_in_window(events: List[Tuple[datetime.datetime, str]], window_seconds: float) -> int:
    """Largest number of distinct counterparties seen inside any sliding time window."""
    events = sorted(events, key=lambda x: x[0])
    best = 0
    start = 0
    for end in range(len(events)):
        while (events[end][0] - events[start][0]).total_seconds() > window_seconds:
            start += 1
        best = max(best, len({c for _, c in events[start:end + 1]}))
    return best


def detect_fan_in(
    graph: nx.DiGraph,
    min_in_degree: int = 4,
    min_in_out_ratio: float = 2.0,
    burst_window_seconds: Optional[float] = 2 * 3600.0,
) -> PatternDetectionResult:
    """Detects Fan-In patterns: Multiple accounts funneling money into a single collector account.

    An account is flagged if:
    1. Its in_degree >= min_in_degree,
    2. Its in_degree to out_degree ratio >= min_in_out_ratio (or out_degree is 0), and
    3. At least min_in_degree distinct senders paid it within burst_window_seconds
       (set burst_window_seconds=None to skip the timing check).
    """
    flagged = []
    details = []

    for node in graph.nodes():
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)

        if in_deg >= min_in_degree:
            ratio = float(in_deg) / (out_deg if out_deg > 0 else 0.5)
            burst = None
            if burst_window_seconds is not None:
                events = [(dt, u) for u in graph.predecessors(node) for dt, _ in _edge_transactions(graph, u, node)]
                burst = _max_distinct_in_window(events, burst_window_seconds)
            if ratio >= min_in_out_ratio and (burst is None or burst >= min_in_degree):
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
                    "max_senders_in_burst_window": burst,
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
    burst_window_seconds: Optional[float] = 2 * 3600.0,
) -> PatternDetectionResult:
    """Detects Fan-Out patterns: A single account dispersing money to multiple distinct accounts.

    An account is flagged if:
    1. Its out_degree >= min_out_degree,
    2. Its out_degree to in_degree ratio >= min_out_in_ratio (or in_degree is 0), and
    3. It paid at least min_out_degree distinct receivers within burst_window_seconds
       (set burst_window_seconds=None to skip the timing check).
    """
    flagged = []
    details = []

    for node in graph.nodes():
        in_deg = graph.in_degree(node)
        out_deg = graph.out_degree(node)

        if out_deg >= min_out_degree:
            ratio = float(out_deg) / (in_deg if in_deg > 0 else 0.5)
            burst = None
            if burst_window_seconds is not None:
                events = [(dt, v) for v in graph.successors(node) for dt, _ in _edge_transactions(graph, node, v)]
                burst = _max_distinct_in_window(events, burst_window_seconds)
            if ratio >= min_out_in_ratio and (burst is None or burst >= min_out_degree):
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
                    "max_receivers_in_burst_window": burst,
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


def _edge_transactions(graph: nx.DiGraph, u: str, v: str) -> List[Tuple[datetime.datetime, float]]:
    """Returns the (timestamp, amount) pairs of every transaction on edge u -> v, oldest first."""
    pairs = []
    for t in graph[u][v].get("transactions", []):
        dt = parse_iso_timestamp(t.get("timestamp"))
        if dt is not None:
            pairs.append((dt, float(t.get("amount", 0.0))))
    pairs.sort(key=lambda x: x[0])
    return pairs


def _find_time_ordered_loop(
    graph: nx.DiGraph,
    cycle: List[str],
    max_window_seconds: float,
    min_retention: float,
    max_growth: float,
) -> Optional[List[Dict[str, Any]]]:
    """Looks for real money moving around the cycle: each hop happens after the previous one,
    the whole loop closes within the time window, and each hop carries a comparable amount
    (between min_retention and max_growth times the previous hop).

    Returns the hop-by-hop path if such a flow exists, otherwise None. Structural loops made of
    unrelated payments (common in ordinary peer-to-peer traffic) fail this check.
    """
    n = len(cycle)
    edges = [(cycle[i], cycle[(i + 1) % n]) for i in range(n)]
    edge_txs = {e: _edge_transactions(graph, *e) for e in edges}

    for rotation in range(n):
        ordered_edges = edges[rotation:] + edges[:rotation]
        for start_dt, start_amount in edge_txs[ordered_edges[0]]:
            hops = [{"from": ordered_edges[0][0], "to": ordered_edges[0][1], "amount": start_amount, "timestamp": start_dt.isoformat()}]
            prev_dt, prev_amount = start_dt, start_amount
            for u, v in ordered_edges[1:]:
                next_hop = None
                for dt, amount in edge_txs[(u, v)]:
                    if dt < prev_dt or (dt - start_dt).total_seconds() > max_window_seconds:
                        continue
                    if min_retention * prev_amount <= amount <= max_growth * prev_amount:
                        next_hop = (dt, amount)
                        break
                if next_hop is None:
                    break
                prev_dt, prev_amount = next_hop
                hops.append({"from": u, "to": v, "amount": prev_amount, "timestamp": prev_dt.isoformat()})
            if len(hops) == n:
                return hops
    return None


def detect_circular_flows(
    graph: nx.DiGraph,
    min_cycle_length: int = 3,
    max_cycle_length: int = 6,
    max_cycles_to_search: int = 50,
    max_window_seconds: float = 6 * 3600.0,
    min_retention: float = 0.5,
    max_growth: float = 1.1,
    max_candidate_cycles: int = 5000,
) -> PatternDetectionResult:
    """Detects circular fund flows (e.g. A -> B -> C -> A) where money actually travels the loop.

    A structural cycle is only flagged when a time-ordered sequence of transactions moves a
    comparable amount all the way around it within max_window_seconds. Cycles of length
    >= min_cycle_length are considered to distinguish layering loops from simple reciprocal
    payments (length 2).
    """
    flagged_set: Set[str] = set()
    details = []

    try:
        # Relabel nodes to integers in sorted order: simple_cycles walks internal sets, so with
        # string node IDs the order it yields cycles in (and which ones survive the caps below)
        # changes with Python's per-process hash seed. Integer labels make the result reproducible.
        ordered_nodes = sorted(graph.nodes(), key=str)
        index_graph = nx.relabel_nodes(graph, {n: i for i, n in enumerate(ordered_nodes)}, copy=True)
        try:
            cycles_generator = nx.simple_cycles(index_graph, length_bound=max_cycle_length)
        except TypeError:  # networkx < 3.1 has no length_bound
            cycles_generator = nx.simple_cycles(index_graph)
        candidates_checked = 0
        for index_cycle in cycles_generator:
            cycle = [ordered_nodes[i] for i in index_cycle]
            cycle_len = len(cycle)
            if not (min_cycle_length <= cycle_len <= max_cycle_length):
                continue
            candidates_checked += 1
            if candidates_checked > max_candidate_cycles:
                break
            hops = _find_time_ordered_loop(graph, cycle, max_window_seconds, min_retention, max_growth)
            if hops is None:
                continue
            flagged_set.update(cycle)
            first_dt = parse_iso_timestamp(hops[0]["timestamp"])
            last_dt = parse_iso_timestamp(hops[-1]["timestamp"])
            details.append({
                "cycle_path": cycle + [cycle[0]],
                "length": cycle_len,
                "nodes": cycle,
                "hops": hops,
                "loop_duration_seconds": round((last_dt - first_dt).total_seconds(), 1),
                "amount_retained_ratio": round(hops[-1]["amount"] / hops[0]["amount"], 3),
            })
            if len(details) >= max_cycles_to_search:
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
        description=f"Detected {len(details)} time-ordered circular flow(s) involving {len(flagged_list)} account(s).",
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
    max_amount_ratio: float = 1.10,  # Outflow <= 110% of inflow (same money, not unrelated payments)
    min_amount: float = 1000.0,  # Ignore small everyday payments
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
                if 0 <= time_diff <= time_window_seconds and in_tx["amount"] >= min_amount:
                    # Check amount similarity (e.g. forward 70% to 110%)
                    if in_tx["amount"] * amount_tolerance_ratio <= out_tx["amount"] <= in_tx["amount"] * max_amount_ratio:
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


def detect_structuring(
    graph: nx.DiGraph,
    reporting_threshold: float = 10000.0,
    near_threshold_ratio: float = 0.85,
    min_transactions: int = 3,
    time_window_seconds: float = 24 * 3600.0,
) -> PatternDetectionResult:
    """Detects structuring (smurfing): a large sum split into several transactions that each stay
    just under a monitoring or reporting threshold.

    An account is flagged if, within time_window_seconds, it sends (splitter) or receives
    (collector) at least min_transactions transactions whose amounts fall in
    [near_threshold_ratio * reporting_threshold, reporting_threshold), and those transactions
    together exceed the threshold.

    reporting_threshold is a prototype setting (BDT) for synthetic data, not an official limit.
    """
    band_low = near_threshold_ratio * reporting_threshold
    flagged_set: Set[str] = set()
    details = []

    def best_window(events: List[Tuple[datetime.datetime, float, str]]) -> List[Tuple[datetime.datetime, float, str]]:
        events = sorted(events, key=lambda x: x[0])
        best: List[Tuple[datetime.datetime, float, str]] = []
        start = 0
        for end in range(len(events)):
            while (events[end][0] - events[start][0]).total_seconds() > time_window_seconds:
                start += 1
            if end - start + 1 > len(best):
                best = events[start:end + 1]
        return best

    for node in sorted(graph.nodes(), key=str):
        for role, neighbors, edge_of in (
            ("splitter", graph.successors(node), lambda n: (node, n)),
            ("collector", graph.predecessors(node), lambda n: (n, node)),
        ):
            events = [
                (dt, amount, n)
                for n in neighbors
                for dt, amount in _edge_transactions(graph, *edge_of(n))
                if band_low <= amount < reporting_threshold
            ]
            window = best_window(events)
            total = sum(a for _, a, _ in window)
            if len(window) >= min_transactions and total > reporting_threshold:
                flagged_set.add(node)
                details.append({
                    "account_id": node,
                    "role": role,
                    "near_threshold_count": len(window),
                    "total_amount": round(total, 2),
                    "largest_amount": round(max(a for _, a, _ in window), 2),
                    "reporting_threshold": reporting_threshold,
                    "window_start": window[0][0].isoformat(),
                    "window_end": window[-1][0].isoformat(),
                    "counterparties": sorted({n for _, _, n in window}),
                })

    flagged_list = sorted(list(flagged_set))
    return PatternDetectionResult(
        pattern_name="structuring",
        detected=len(flagged_list) > 0,
        flagged_accounts=flagged_list,
        details=details,
        description=(
            f"Identified {len(flagged_list)} account(s) moving {min_transactions}+ transactions just under the "
            f"{reporting_threshold:,.0f} threshold within {int(time_window_seconds / 3600)} hours."
        ),
    )


def detect_coordinated_networks(
    graph: nx.DiGraph,
    min_cluster_size: int = 4,
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


# Above this many accounts, enumerating cycles and paths on the static graph stops being
# feasible (the search caps cut it off before it reaches the suspicious part of the network),
# so circular flows and chains are found by replaying transactions in time order instead.
TEMPORAL_MODE_NODE_LIMIT = 2000


def detect_temporal_flows(
    graph: nx.DiGraph,
    min_fast_hops: int = 3,
    min_slow_hops: int = 4,
    max_details: int = 200,
) -> Tuple[PatternDetectionResult, PatternDetectionResult]:
    """Circular flows and transaction chains from time-ordered flow tracing (ml.temporal_flow).

    A chain is flagged when money moves through `min_fast_hops` linked payments with at most
    an hour between hops, or `min_slow_hops` with at most 12 hours between hops. A circular
    flow is flagged when such a chain returns to an account already on it. One linear pass over
    the transactions, so it scales where exhaustive search does not.
    """
    from ml.temporal_flow import FAST_WINDOW_SECONDS, SLOW_WINDOW_SECONDS, trace_flows

    nodes = sorted(graph.nodes(), key=str)
    index = {node: i for i, node in enumerate(nodes)}
    rows = []
    for u, v, data in graph.edges(data=True):
        for t in data.get("transactions", []):
            dt = parse_iso_timestamp(t.get("timestamp"))
            if dt is not None:
                rows.append((dt.timestamp(), index[u], index[v], float(t.get("amount", 0.0))))
    rows.sort()
    times = [row[0] for row in rows]
    senders = [row[1] for row in rows]
    receivers = [row[2] for row in rows]
    amounts = [row[3] for row in rows]

    fast = trace_flows(senders, receivers, amounts, times, len(nodes), FAST_WINDOW_SECONDS, min_chain_hops=min_fast_hops, keep_details=max_details)
    slow = trace_flows(senders, receivers, amounts, times, len(nodes), SLOW_WINDOW_SECONDS, min_chain_hops=min_slow_hops, keep_details=max_details)

    cycle_flagged = sorted(nodes[i] for i in range(len(nodes)) if fast.cycle_count[i] > 0 or slow.cycle_count[i] > 0)
    cycle_details = []
    seen_loops = set()
    for found in fast.cycles + slow.cycles:
        loop = [nodes[i] for i in found["nodes"]]
        key = frozenset(loop)
        if key in seen_loops:
            continue
        seen_loops.add(key)
        cycle_details.append({
            "cycle_path": loop + [loop[0]],
            "length": len(loop),
            "nodes": loop,
            "hops": [],
            "loop_duration_seconds": round(found["duration_seconds"], 1),
            "amount_retained_ratio": round(found["closing_amount"] / max(found["first_amount"], 1e-9), 3),
        })

    chain_flagged = sorted(
        nodes[i] for i in range(len(nodes))
        if fast.chain_length[i] >= min_fast_hops or slow.chain_length[i] >= min_slow_hops
    )
    chain_details = []
    for found in fast.chains + slow.chains:
        path = [nodes[i] for i in found["path"]]
        chain_details.append({"chain_path": path, "hops": found["hops"], "start": path[0], "end": path[-1]})
    # Per-account chain length for accounts whose own chain was not kept in the capped detail list
    chain_lengths = {
        nodes[i]: int(max(fast.chain_length[i], slow.chain_length[i])) for i in range(len(nodes))
        if fast.chain_length[i] >= min_fast_hops or slow.chain_length[i] >= min_slow_hops
    }

    circular = PatternDetectionResult(
        pattern_name="circular_flow",
        detected=len(cycle_flagged) > 0,
        flagged_accounts=cycle_flagged,
        details=cycle_details,
        description=f"Detected time-ordered circular flow(s) involving {len(cycle_flagged)} account(s) (temporal tracing).",
    )
    chains = PatternDetectionResult(
        pattern_name="transaction_chain",
        detected=len(chain_flagged) > 0,
        flagged_accounts=chain_flagged,
        details=chain_details,
        description=f"Identified time-ordered flow chain(s) across {len(chain_flagged)} account(s) (temporal tracing).",
    )
    chains.chain_lengths = chain_lengths  # type: ignore[attr-defined]
    return circular, chains


def run_all_network_detections(graph: nx.DiGraph, temporal: Optional[bool] = None) -> Dict[str, PatternDetectionResult]:
    """Executes all pattern detection algorithms against the provided transaction graph.

    temporal=None picks the mode by graph size: exhaustive search on small graphs (the demo
    scenarios), time-ordered flow tracing on large ones.
    """
    if temporal is None:
        temporal = graph.number_of_nodes() > TEMPORAL_MODE_NODE_LIMIT
    if temporal:
        circular, chains = detect_temporal_flows(graph)
    else:
        circular, chains = detect_circular_flows(graph), detect_transaction_chains(graph)
    return {
        "fan_in": detect_fan_in(graph),
        "fan_out": detect_fan_out(graph),
        "circular_flow": circular,
        "transaction_chain": chains,
        "rapid_movement": detect_rapid_movement(graph),
        "structuring": detect_structuring(graph),
        "coordinated_network": detect_coordinated_networks(graph),
    }
