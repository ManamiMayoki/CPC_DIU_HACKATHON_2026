"""Vectorised account feature store for large transaction networks.

Builds one row per account from a transaction table, in four feature families:

  transactional   volumes, counts, ratios, near-threshold counts (what a rules engine can see)
  temporal        when and how fast: bursts, night share, inter-arrival rhythm, dwell time
  graph           who is connected to whom: degrees, reciprocity, PageRank, triads, SCC size,
                  and time-respecting flow chains / cycles from ml.temporal_flow
  neighbourhood   2-hop message passing: each account also gets the average of its neighbours'
                  key features (the aggregation step of a GraphSAGE-style GNN, without the
                  learned weights), so a quiet mule surrounded by suspicious flow still stands out

Everything is pandas / numpy / scipy.sparse, so it runs on hundreds of thousands of
transactions in seconds and has no dependency on NetworkX path enumeration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import connected_components

from ml.temporal_flow import FAST_WINDOW_SECONDS, SLOW_WINDOW_SECONDS, trace_flows

DEFAULT_THRESHOLD = 10000.0

TRANSACTIONAL_FEATURES = [
    "transaction_count", "sent_count", "received_count", "total_incoming", "total_outgoing", "net_flow",
    "average_transaction_amount", "maximum_transaction_amount", "std_transaction_amount",
    "incoming_outgoing_ratio", "passthrough_ratio", "flow_imbalance_magnitude", "counterparty_diversity",
    "amount_volatility", "near_threshold_out", "near_threshold_in", "sub_threshold_share", "round_amount_share",
]
TEMPORAL_FEATURES = [
    "active_days", "active_span_hours", "transaction_velocity", "max_tx_per_hour", "max_senders_2h",
    "max_receivers_2h", "night_share", "hour_entropy", "inter_arrival_median_s", "inter_arrival_cv",
    "burstiness", "same_day_turnover", "dwell_fast_s", "dwell_slow_s",
]
GRAPH_FEATURES = [
    "in_degree", "out_degree", "degree_ratio", "reciprocity", "pagerank", "scc_size", "triad_cycles",
    "two_hop_out", "two_hop_in", "avg_neighbor_degree",
    "forward_count_fast", "forward_share_fast", "chain_length_fast", "cycle_count_fast",
    "forward_count_slow", "forward_share_slow", "chain_length_slow", "cycle_count_slow",
]
# Features whose neighbourhood averages are added by message passing
MESSAGE_BASE = [
    "log_total_incoming", "log_total_outgoing", "passthrough_ratio", "chain_length_slow", "forward_share_slow",
    "near_threshold_total", "cycle_count_slow", "night_share", "log_in_degree", "log_out_degree",
]
NEIGHBOURHOOD_FEATURES = (
    [f"nb_in_{f}" for f in MESSAGE_BASE] + [f"nb_out_{f}" for f in MESSAGE_BASE] + [f"nb2_{f}" for f in MESSAGE_BASE]
)
TIER_FEATURES = ["tier_personal", "tier_agent", "tier_merchant"]

FEATURE_FAMILIES = {
    "transactional": TRANSACTIONAL_FEATURES,
    "temporal": TEMPORAL_FEATURES,
    "graph": GRAPH_FEATURES,
    "neighbourhood": NEIGHBOURHOOD_FEATURES,
    "account_type": TIER_FEATURES,
}


def feature_family(name: str) -> str:
    for family, names in FEATURE_FAMILIES.items():
        if name in names:
            return family
    return "other"


def transactions_to_frame(transactions: Union[List[Dict[str, Any]], pd.DataFrame]) -> pd.DataFrame:
    """Normalises input to a frame with sender, receiver, amount, t (seconds) sorted by time."""
    df = transactions if isinstance(transactions, pd.DataFrame) else pd.DataFrame(transactions)
    df = df.rename(columns={"sender_id": "sender", "receiver_id": "receiver"})
    out = pd.DataFrame({
        "sender": df["sender"].astype(str).values,
        "receiver": df["receiver"].astype(str).values,
        "amount": df["amount"].astype(float).values,
    })
    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    out["t"] = (ts - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().values
    out = out.dropna(subset=["t"])
    out = out[(out["amount"] > 0) & (out["sender"] != out["receiver"])]
    return out.sort_values("t", kind="stable").reset_index(drop=True)


def _group_max_distinct(account: np.ndarray, bucket: np.ndarray, other: np.ndarray, n: int) -> np.ndarray:
    """Max number of distinct counterparties an account has inside any one time bucket."""
    frame = pd.DataFrame({"a": account, "b": bucket, "o": other}).drop_duplicates()
    counts = frame.groupby(["a", "b"]).size().groupby(level=0).max()
    result = np.zeros(n)
    result[counts.index.values] = counts.values
    return result


def _pagerank(adj: sparse.csr_matrix, damping: float = 0.85, iterations: int = 30) -> np.ndarray:
    n = adj.shape[0]
    out_weight = np.asarray(adj.sum(axis=1)).ravel()
    inv = np.divide(1.0, out_weight, out=np.zeros(n), where=out_weight > 0)
    transition = sparse.diags(inv) @ adj
    rank = np.full(n, 1.0 / n)
    dangling = out_weight == 0
    for _ in range(iterations):
        rank = (1 - damping) / n + damping * (transition.T @ rank + rank[dangling].sum() / n)
    return rank * n  # 1.0 = average account


def build_account_features(
    transactions: Union[List[Dict[str, Any]], pd.DataFrame],
    tiers: Optional[Dict[str, str]] = None,
    threshold: float = DEFAULT_THRESHOLD,
    return_flows: bool = False,
):
    """Returns a DataFrame indexed by account_id with every feature family.

    tiers maps account_id -> "personal" | "agent" | "merchant" (KYC account type); unknown
    accounts default to personal.
    """
    tx = transactions_to_frame(transactions)
    accounts, inverse = np.unique(np.concatenate([tx["sender"].values, tx["receiver"].values]), return_inverse=True)
    n = len(accounts)
    m = len(tx)
    s = inverse[:m]
    r = inverse[m:]
    amount = tx["amount"].values
    t = tx["t"].values
    t0 = t.min() if m else 0.0

    def agg(index: np.ndarray, values: Optional[np.ndarray] = None) -> np.ndarray:
        return np.bincount(index, weights=values, minlength=n).astype(float)

    sent_count = agg(s)
    recv_count = agg(r)
    total_out = agg(s, amount)
    total_in = agg(r, amount)
    tx_count = sent_count + recv_count
    volume = total_in + total_out

    # Long form: one row per (account, transaction) regardless of direction
    acc_long = np.concatenate([s, r])
    amt_long = np.concatenate([amount, amount])
    t_long = np.concatenate([t, t])
    other_long = np.concatenate([r, s])
    long = pd.DataFrame({"a": acc_long, "amount": amt_long, "t": t_long})
    grouped = long.groupby("a")["amount"]
    max_amount = np.zeros(n)
    std_amount = np.zeros(n)
    stats = grouped.agg(["max", "std"])
    max_amount[stats.index.values] = stats["max"].values
    std_amount[stats.index.values] = np.nan_to_num(stats["std"].values)
    avg_amount = volume / np.maximum(tx_count, 1)

    counterparties = pd.DataFrame({"a": acc_long, "o": other_long}).drop_duplicates().groupby("a").size()
    unique_cp = np.zeros(n)
    unique_cp[counterparties.index.values] = counterparties.values

    band_low = 0.85 * threshold
    near = (amount >= band_low) & (amount < threshold)
    sub = (amount >= 0.5 * threshold) & (amount < threshold)
    near_out = agg(s[near])
    near_in = agg(r[near])
    sub_share = (agg(s[sub]) + agg(r[sub])) / np.maximum(tx_count, 1)
    is_round = (np.mod(amount, 500) == 0)
    round_share = (agg(s[is_round]) + agg(r[is_round])) / np.maximum(tx_count, 1)

    max_flow = np.maximum(total_in, total_out)
    features: Dict[str, np.ndarray] = {
        "transaction_count": tx_count,
        "sent_count": sent_count,
        "received_count": recv_count,
        "total_incoming": total_in,
        "total_outgoing": total_out,
        "net_flow": total_in - total_out,
        "average_transaction_amount": avg_amount,
        "maximum_transaction_amount": max_amount,
        "std_transaction_amount": std_amount,
        "incoming_outgoing_ratio": total_in / (total_out + 1.0),
        "passthrough_ratio": np.where(max_flow > 0, np.minimum(total_in, total_out) / (max_flow + 1e-6), 0.0),
        "flow_imbalance_magnitude": np.where(volume > 0, np.abs(total_in - total_out) / (volume + 1e-6), 0.0),
        "counterparty_diversity": unique_cp / np.maximum(tx_count, 1),
        "amount_volatility": np.where(avg_amount > 0, std_amount / (avg_amount + 1e-6), 0.0),
        "near_threshold_out": near_out,
        "near_threshold_in": near_in,
        "sub_threshold_share": sub_share,
        "round_amount_share": round_share,
    }

    # ---------------------------------------------------------------- temporal
    hour_bucket = np.floor(t_long / 3600.0).astype(np.int64)
    day_bucket = np.floor((t_long - t0) / 86400.0).astype(np.int64)
    hour_of_day = (hour_bucket % 24).astype(int)

    per_hour = pd.Series(1, index=pd.MultiIndex.from_arrays([acc_long, hour_bucket])).groupby(level=[0, 1]).sum()
    max_per_hour = np.zeros(n)
    mph = per_hour.groupby(level=0).max()
    max_per_hour[mph.index.values] = mph.values

    active_days = np.zeros(n)
    ad = pd.DataFrame({"a": acc_long, "d": day_bucket}).drop_duplicates().groupby("a").size()
    active_days[ad.index.values] = ad.values

    first = np.full(n, np.inf)
    last = np.full(n, -np.inf)
    np.minimum.at(first, acc_long, t_long)
    np.maximum.at(last, acc_long, t_long)
    span_hours = np.maximum((last - first) / 3600.0, 0.0)

    night = (hour_of_day < 6)
    night_share = agg(acc_long[night]) / np.maximum(tx_count, 1)

    hod_counts = np.zeros((n, 24))
    np.add.at(hod_counts, (acc_long, hour_of_day), 1.0)
    prob = hod_counts / np.maximum(hod_counts.sum(axis=1, keepdims=True), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        hour_entropy = -np.nansum(np.where(prob > 0, prob * np.log(prob), 0.0), axis=1)

    order = np.lexsort((t_long, acc_long))
    a_sorted = acc_long[order]
    t_sorted = t_long[order]
    gaps = np.diff(t_sorted)
    same = a_sorted[1:] == a_sorted[:-1]
    gap_frame = pd.DataFrame({"a": a_sorted[1:][same], "gap": gaps[same]})
    gap_stats = gap_frame.groupby("a")["gap"].agg(["median", "mean", "std"])
    iat_median = np.full(n, -1.0)
    iat_cv = np.zeros(n)
    burstiness = np.zeros(n)
    idx = gap_stats.index.values
    iat_median[idx] = gap_stats["median"].values
    g_mean = gap_stats["mean"].values
    g_std = np.nan_to_num(gap_stats["std"].values)
    iat_cv[idx] = g_std / (g_mean + 1e-6)
    burstiness[idx] = (g_std - g_mean) / (g_std + g_mean + 1e-6)

    two_hour = np.floor(t / 7200.0).astype(np.int64)
    max_senders_2h = _group_max_distinct(r, two_hour, s, n)
    max_receivers_2h = _group_max_distinct(s, two_hour, r, n)

    # Same-day turnover: how much of what arrives leaves again the same day
    day_tx = np.floor((t - t0) / 86400.0).astype(np.int64)
    daily_in = pd.Series(amount, index=pd.MultiIndex.from_arrays([r, day_tx])).groupby(level=[0, 1]).sum()
    daily_out = pd.Series(amount, index=pd.MultiIndex.from_arrays([s, day_tx])).groupby(level=[0, 1]).sum()
    turned = pd.concat([daily_in, daily_out], axis=1, keys=["i", "o"]).fillna(0.0).min(axis=1).groupby(level=0).sum()
    same_day_turnover = np.zeros(n)
    same_day_turnover[turned.index.values] = turned.values
    same_day_turnover = same_day_turnover / (total_in + 1.0)

    # ------------------------------------------------------- temporal flow tracing
    s_list, r_list, a_list, t_list = s.tolist(), r.tolist(), amount.tolist(), t.tolist()
    fast = trace_flows(s_list, r_list, a_list, t_list, n, window_seconds=FAST_WINDOW_SECONDS)
    slow = trace_flows(s_list, r_list, a_list, t_list, n, window_seconds=SLOW_WINDOW_SECONDS)

    features.update({
        "active_days": active_days,
        "active_span_hours": span_hours,
        "transaction_velocity": tx_count / np.maximum(span_hours, 0.1),
        "max_tx_per_hour": max_per_hour,
        "max_senders_2h": max_senders_2h,
        "max_receivers_2h": max_receivers_2h,
        "night_share": night_share,
        "hour_entropy": hour_entropy,
        "inter_arrival_median_s": iat_median,
        "inter_arrival_cv": iat_cv,
        "burstiness": burstiness,
        "same_day_turnover": same_day_turnover,
        "dwell_fast_s": fast.median_like_dwell(),
        "dwell_slow_s": slow.median_like_dwell(),
    })

    # ------------------------------------------------------------------- graph
    edge_weight = sparse.coo_matrix((amount, (s, r)), shape=(n, n)).tocsr()  # duplicates are summed
    adj = edge_weight.copy()
    adj.data[:] = 1.0
    in_degree = np.asarray(adj.sum(axis=0)).ravel()
    out_degree = np.asarray(adj.sum(axis=1)).ravel()
    mutual = adj.multiply(adj.T)
    reciprocity = np.asarray(mutual.sum(axis=1)).ravel() / np.maximum(unique_cp, 1)
    _, scc_labels = connected_components(adj, directed=True, connection="strong")
    scc_size = np.bincount(scc_labels)[scc_labels].astype(float)
    two = adj @ adj
    two_hop_out = np.diff(two.indptr).astype(float)
    two_hop_in = np.diff(two.T.tocsr().indptr).astype(float)
    triad_cycles = np.asarray(two.multiply(adj.T).sum(axis=1)).ravel()  # directed 3-cycles through the node
    undirected = ((adj + adj.T) > 0).astype(float)
    total_degree = np.asarray(undirected.sum(axis=1)).ravel()
    avg_neighbor_degree = (undirected @ total_degree) / np.maximum(total_degree, 1)

    features.update({
        "in_degree": in_degree,
        "out_degree": out_degree,
        "degree_ratio": in_degree / (out_degree + 1.0),
        "reciprocity": reciprocity,
        "pagerank": _pagerank(edge_weight),
        "scc_size": scc_size,
        "triad_cycles": triad_cycles,
        "two_hop_out": two_hop_out,
        "two_hop_in": two_hop_in,
        "avg_neighbor_degree": avg_neighbor_degree,
        "forward_count_fast": fast.forward_count.astype(float),
        "forward_share_fast": fast.forwarded_amount / (total_in + 1.0),
        "chain_length_fast": fast.chain_length.astype(float),
        "cycle_count_fast": fast.cycle_count.astype(float),
        "forward_count_slow": slow.forward_count.astype(float),
        "forward_share_slow": slow.forwarded_amount / (total_in + 1.0),
        "chain_length_slow": slow.chain_length.astype(float),
        "cycle_count_slow": slow.cycle_count.astype(float),
    })

    # ------------------------------------------- neighbourhood message passing
    base = {
        "log_total_incoming": np.log1p(total_in),
        "log_total_outgoing": np.log1p(total_out),
        "passthrough_ratio": features["passthrough_ratio"],
        "chain_length_slow": features["chain_length_slow"],
        "forward_share_slow": np.minimum(features["forward_share_slow"], 2.0),
        "near_threshold_total": near_out + near_in,
        "cycle_count_slow": np.minimum(features["cycle_count_slow"], 10.0),
        "night_share": night_share,
        "log_in_degree": np.log1p(in_degree),
        "log_out_degree": np.log1p(out_degree),
    }
    base_matrix = np.column_stack([base[name] for name in MESSAGE_BASE])
    mean_over_senders = sparse.diags(1.0 / np.maximum(in_degree, 1)) @ adj.T      # row i averages i's payers
    mean_over_receivers = sparse.diags(1.0 / np.maximum(out_degree, 1)) @ adj     # row i averages i's payees
    mean_over_all = sparse.diags(1.0 / np.maximum(total_degree, 1)) @ undirected
    nb_in = mean_over_senders @ base_matrix
    nb_out = mean_over_receivers @ base_matrix
    nb2 = mean_over_all @ (mean_over_all @ base_matrix)
    for j, name in enumerate(MESSAGE_BASE):
        features[f"nb_in_{name}"] = nb_in[:, j]
        features[f"nb_out_{name}"] = nb_out[:, j]
        features[f"nb2_{name}"] = nb2[:, j]

    tiers = tiers or {}
    tier_values = np.array([tiers.get(acc, "personal") for acc in accounts])
    for tier in ("personal", "agent", "merchant"):
        features[f"tier_{tier}"] = (tier_values == tier).astype(float)

    frame = pd.DataFrame(features, index=pd.Index(accounts, name="account_id")).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    if return_flows:
        return frame, {"fast": fast, "slow": slow, "accounts": accounts}
    return frame


def family_columns(families: Sequence[str]) -> List[str]:
    columns: List[str] = []
    for family in families:
        columns.extend(FEATURE_FAMILIES[family])
    return columns
