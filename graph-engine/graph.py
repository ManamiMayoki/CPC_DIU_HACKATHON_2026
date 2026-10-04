"""Transaction Graph Module using NetworkX.

Builds directed transaction graphs from validated synthetic financial transactions.
Nodes represent accounts; directed edges represent monetary transfers (sender -> receiver).
Edge attributes contain: amount, timestamp, transaction_id.
"""

from __future__ import annotations

import datetime
import os
import sys
from typing import Any, Dict, List, Optional, Union
import networkx as nx
import pandas as pd

# Ensure project root is available on sys.path for validation imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.validation import parse_iso_timestamp


def _normalize_timestamp(raw_timestamp: Any) -> tuple[str, Optional[datetime.datetime]]:
    """Normalizes raw timestamp inputs (ISO string, datetime, epoch) into a validated ISO-8601 string and datetime object."""
    if raw_timestamp is None:
        return "", None

    parsed_dt = parse_iso_timestamp(raw_timestamp)
    if parsed_dt is not None:
        return parsed_dt.isoformat(), parsed_dt

    # Fallback to string representation if unparseable
    return str(raw_timestamp).strip(), None


def build_transaction_graph(
    transactions: Union[List[Dict[str, Any]], pd.DataFrame],
    multi_graph: bool = False,
) -> Union[nx.DiGraph, nx.MultiDiGraph]:
    """Constructs a NetworkX directed graph from a collection of transactions.

    Args:
        transactions: List of transaction dictionaries or DataFrame with:
            - 'sender_id'
            - 'receiver_id'
            - 'amount'
            - 'timestamp'
            - 'transaction_id' (optional)
        multi_graph: If True, returns nx.MultiDiGraph retaining every individual edge.
            If False, returns nx.DiGraph aggregating multiple edges between the same
            pair into total amount and transaction count, while preserving transaction details in a list.

    Returns:
        nx.DiGraph or nx.MultiDiGraph
    """
    if isinstance(transactions, pd.DataFrame):
        tx_records = transactions.to_dict(orient="records")
    else:
        tx_records = transactions

    if multi_graph:
        graph = nx.MultiDiGraph()
        for tx in tx_records:
            sender = str(tx.get("sender_id") or tx.get("sender"))
            receiver = str(tx.get("receiver_id") or tx.get("receiver"))
            amount = float(tx.get("amount", 0.0))
            iso_timestamp, _ = _normalize_timestamp(tx.get("timestamp"))
            tx_id = str(tx.get("transaction_id") or tx.get("tx_id", ""))

            graph.add_node(sender, account_id=sender)
            graph.add_node(receiver, account_id=receiver)

            edge_attr = {
                "amount": amount,
                "timestamp": iso_timestamp,
                "transaction_id": tx_id,
            }
            graph.add_edge(sender, receiver, **edge_attr)
        return graph

    # Aggregated nx.DiGraph
    graph = nx.DiGraph()
    for tx in tx_records:
        sender = str(tx.get("sender_id") or tx.get("sender"))
        receiver = str(tx.get("receiver_id") or tx.get("receiver"))
        amount = float(tx.get("amount", 0.0))
        iso_timestamp, parsed_dt = _normalize_timestamp(tx.get("timestamp"))
        tx_id = str(tx.get("transaction_id") or tx.get("tx_id", ""))

        if not graph.has_node(sender):
            graph.add_node(sender, account_id=sender)
        if not graph.has_node(receiver):
            graph.add_node(receiver, account_id=receiver)

        tx_detail = {
            "transaction_id": tx_id,
            "amount": amount,
            "timestamp": iso_timestamp,
        }

        if graph.has_edge(sender, receiver):
            edge_data = graph[sender][receiver]
            edge_data["weight"] = round(edge_data.get("weight", 0.0) + amount, 4)
            edge_data["count"] = edge_data.get("count", 0) + 1
            edge_data["transactions"].append(tx_detail)

            # Robust chronological comparison to maintain latest timestamp on aggregated edge
            current_latest_str = edge_data.get("timestamp", "")
            current_latest_dt = parse_iso_timestamp(current_latest_str)

            if parsed_dt is not None and current_latest_dt is not None:
                if parsed_dt > current_latest_dt:
                    edge_data["timestamp"] = iso_timestamp
            elif iso_timestamp > current_latest_str:
                edge_data["timestamp"] = iso_timestamp
        else:
            graph.add_edge(
                sender,
                receiver,
                weight=round(amount, 4),
                count=1,
                timestamp=iso_timestamp,
                transaction_id=tx_id,
                transactions=[tx_detail],
            )

    return graph


def get_graph_summary(graph: Union[nx.DiGraph, nx.MultiDiGraph]) -> Dict[str, Any]:
    """Computes high-level summary metrics of the transaction graph."""
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    is_directed = graph.is_directed()

    # Weakly and strongly connected components (for directed graphs)
    if is_directed and num_nodes > 0:
        num_weakly_connected = nx.number_weakly_connected_components(graph)
        num_strongly_connected = nx.number_strongly_connected_components(graph)
    else:
        num_weakly_connected = 0
        num_strongly_connected = 0

    density = nx.density(graph) if num_nodes > 1 else 0.0

    return {
        "num_accounts": num_nodes,
        "num_edges": num_edges,
        "is_directed": is_directed,
        "density": round(density, 6),
        "weakly_connected_components": num_weakly_connected,
        "strongly_connected_components": num_strongly_connected,
    }
