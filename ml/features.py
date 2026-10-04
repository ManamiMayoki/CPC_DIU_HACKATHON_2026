"""ML Feature Engineering Layer.

Computes behavioral transaction features per account and merges them with topological
graph features to construct unified feature matrices for anomaly detection models.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from ml.validation import parse_iso_timestamp


def extract_transaction_features(
    transactions: Union[List[Dict[str, Any]], pd.DataFrame],
) -> pd.DataFrame:
    """Extracts account-level behavioral features from raw transaction records.

    Features generated per account:
    - transaction_count: Total transactions involving this account
    - sent_count: Number of sent transactions
    - received_count: Number of received transactions
    - total_incoming: Total monetary value received
    - total_outgoing: Total monetary value sent
    - net_flow: total_incoming - total_outgoing
    - average_transaction_amount: Mean amount per transaction
    - maximum_transaction_amount: Maximum single transaction amount
    - std_transaction_amount: Standard deviation of transaction amounts
    - unique_senders: Number of distinct counterparties sending to this account
    - unique_receivers: Number of distinct counterparties receiving from this account
    - incoming_outgoing_ratio: Ratio of total incoming to total outgoing funds
    - transaction_velocity: Transactions per active hour
    - counterparty_diversity: Ratio of unique counterparties to transaction count [0, 1]
    - passthrough_ratio: Balance ratio min(in, out) / max(in, out), elevated in layering passthroughs
    - amount_volatility: Coefficient of variation (std / avg) of transaction amounts
    - flow_imbalance_magnitude: Normalized directional drain/funnel magnitude abs(net_flow) / total_volume
    """
    if isinstance(transactions, pd.DataFrame):
        tx_list = transactions.to_dict(orient="records")
    else:
        tx_list = transactions

    if not tx_list:
        return pd.DataFrame()

    # Aggregate stats per account
    accounts: Dict[str, Dict[str, Any]] = {}

    def get_account_slot(acc_id: str) -> Dict[str, Any]:
        if acc_id not in accounts:
            accounts[acc_id] = {
                "sent_amounts": [],
                "received_amounts": [],
                "senders": set(),
                "receivers": set(),
                "timestamps": [],
            }
        return accounts[acc_id]

    for tx in tx_list:
        sender = str(tx.get("sender_id") or tx.get("sender"))
        receiver = str(tx.get("receiver_id") or tx.get("receiver"))
        amount = float(tx.get("amount", 0.0))
        dt = parse_iso_timestamp(tx.get("timestamp"))

        s_slot = get_account_slot(sender)
        s_slot["sent_amounts"].append(amount)
        s_slot["receivers"].add(receiver)
        if dt:
            s_slot["timestamps"].append(dt)

        r_slot = get_account_slot(receiver)
        r_slot["received_amounts"].append(amount)
        r_slot["senders"].add(sender)
        if dt:
            r_slot["timestamps"].append(dt)

    records: List[Dict[str, Any]] = []

    for acc_id, data in accounts.items():
        sent_arr = np.array(data["sent_amounts"], dtype=float)
        recv_arr = np.array(data["received_amounts"], dtype=float)
        all_arr = np.concatenate([sent_arr, recv_arr]) if (len(sent_arr) + len(recv_arr)) > 0 else np.array([0.0])

        s_count = len(sent_arr)
        r_count = len(recv_arr)
        total_tx = s_count + r_count

        total_in = float(np.sum(recv_arr)) if r_count > 0 else 0.0
        total_out = float(np.sum(sent_arr)) if s_count > 0 else 0.0
        net_flow = total_in - total_out
        total_volume = total_in + total_out

        avg_amount = float(np.mean(all_arr)) if total_tx > 0 else 0.0
        max_amount = float(np.max(all_arr)) if total_tx > 0 else 0.0
        std_amount = float(np.std(all_arr)) if total_tx > 1 else 0.0

        u_senders = len(data["senders"])
        u_receivers = len(data["receivers"])
        total_unique_counterparties = len(data["senders"] | data["receivers"])

        # Ratio incoming / outgoing
        in_out_ratio = (total_in / (total_out + 1.0))

        # Counterparty diversity: unique counterparties / total transactions
        counterparty_diversity = total_unique_counterparties / max(total_tx, 1)

        # Passthrough ratio: near 1.0 indicates high flow turnover (inflow ≈ outflow)
        max_flow = max(total_in, total_out)
        passthrough_ratio = (min(total_in, total_out) / (max_flow + 1e-6)) if max_flow > 0 else 0.0

        # Amount volatility
        amount_volatility = (std_amount / (avg_amount + 1e-6)) if avg_amount > 0 else 0.0

        # Flow imbalance magnitude [0.0, 1.0]
        flow_imbalance = abs(net_flow) / (total_volume + 1e-6) if total_volume > 0 else 0.0

        # Velocity: transactions per hour
        timestamps = sorted(data["timestamps"])
        if len(timestamps) >= 2:
            time_span_hours = max((timestamps[-1] - timestamps[0]).total_seconds() / 3600.0, 0.1)
            velocity = total_tx / time_span_hours
        else:
            velocity = float(total_tx)  # default 1 hour baseline if single burst

        records.append({
            "account_id": acc_id,
            "transaction_count": total_tx,
            "sent_count": s_count,
            "received_count": r_count,
            "total_incoming": round(total_in, 4),
            "total_outgoing": round(total_out, 4),
            "net_flow": round(net_flow, 4),
            "average_transaction_amount": round(avg_amount, 4),
            "maximum_transaction_amount": round(max_amount, 4),
            "std_transaction_amount": round(std_amount, 4),
            "unique_senders": u_senders,
            "unique_receivers": u_receivers,
            "incoming_outgoing_ratio": round(in_out_ratio, 4),
            "transaction_velocity": round(velocity, 4),
            "counterparty_diversity": round(counterparty_diversity, 4),
            "passthrough_ratio": round(passthrough_ratio, 4),
            "amount_volatility": round(amount_volatility, 4),
            "flow_imbalance_magnitude": round(flow_imbalance, 4),
        })

    df = pd.DataFrame(records)
    if not df.empty:
        df.set_index("account_id", inplace=True)
    return df


def build_ml_feature_vector(
    transaction_features: pd.DataFrame,
    graph_features: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Merges behavioral transaction features and topological graph features into a unified ML feature matrix.

    Architecture:
    Transaction Features + Graph Features -> Combined ML Feature Vector
    """
    if transaction_features.empty:
        return pd.DataFrame()

    if graph_features is None or graph_features.empty:
        return transaction_features.copy()

    # Outer join to ensure accounts present in either set are included
    combined = transaction_features.join(graph_features, how="outer")
    # Fill any missing numeric features with 0.0
    combined = combined.fillna(0.0)
    return combined
