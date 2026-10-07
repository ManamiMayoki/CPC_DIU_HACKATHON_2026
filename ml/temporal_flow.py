"""Temporal flow tracing: follow money through accounts in time order.

A static graph says "A paid B and B paid C". It cannot say whether B's payment to C was A's
money. This module replays the transactions in time order and links each outgoing payment to
an earlier incoming payment of the same account when the amount is comparable (70-110%) and
the gap is inside a time window. Linked payments form time-respecting flow chains:

    victim --(t1, 9,000)--> collector --(t1+4min, 8,700)--> mule --(t1+20min, 8,500)--> agent

From those chains it derives, per account: how many payments it forwarded, the longest chain it
sits in, whether money came back to an account already on the chain (a temporal cycle), and
how long money rests before moving on (dwell time).

One pass is O(transactions x inbox size) and needs no cycle enumeration, so unlike exhaustive
cycle/path search on the static graph it keeps working on large networks. Two windows are used:
"fast" (1 hour per hop) for classic rapid layering and "slow" (12 hours per hop) for
low-and-slow movement that deliberately waits out velocity rules.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import numpy as np

FAST_WINDOW_SECONDS = 3600.0
SLOW_WINDOW_SECONDS = 12 * 3600.0
MIN_RATIO = 0.70
MAX_RATIO = 1.10
MIN_AMOUNT = 1000.0
MAX_PATH = 8
MAX_INBOX = 64


@dataclass
class FlowResult:
    """Per-account outputs of one tracing pass (arrays are indexed by account index)."""
    window_seconds: float
    forward_count: np.ndarray
    forwarded_amount: np.ndarray
    chain_length: np.ndarray
    cycle_count: np.ndarray
    dwell_sum: np.ndarray
    cycles: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[Dict[str, Any]] = field(default_factory=list)

    def median_like_dwell(self) -> np.ndarray:
        """Mean dwell time (seconds) of forwarded payments; -1 where nothing was forwarded."""
        return np.where(self.forward_count > 0, self.dwell_sum / np.maximum(self.forward_count, 1), -1.0)


def trace_flows(
    senders: Sequence[int],
    receivers: Sequence[int],
    amounts: Sequence[float],
    times: Sequence[float],
    n_accounts: int,
    window_seconds: float = FAST_WINDOW_SECONDS,
    min_amount: float = MIN_AMOUNT,
    min_chain_hops: int = 3,
    keep_details: int = 200,
) -> FlowResult:
    """Replays transactions (must be sorted by time) and links forwards to earlier receipts.

    senders/receivers are integer account indices in [0, n_accounts). times are seconds.
    Each receipt can fund one forward (it is consumed when matched), which stops a busy agent's
    unrelated cash-ins and cash-outs from chaining endlessly.
    """
    forward_count = np.zeros(n_accounts, dtype=np.int32)
    forwarded_amount = np.zeros(n_accounts, dtype=np.float64)
    chain_length = np.zeros(n_accounts, dtype=np.int32)
    cycle_count = np.zeros(n_accounts, dtype=np.int32)
    dwell_sum = np.zeros(n_accounts, dtype=np.float64)
    cycles: List[Dict[str, Any]] = []
    chains: List[Dict[str, Any]] = []

    # inbox[account] = deque of [time, amount, depth, path (accounts), path_times, path_amounts]
    inbox: List[Any] = [None] * n_accounts

    for i in range(len(senders)):
        u = senders[i]
        v = receivers[i]
        amount = amounts[i]
        t = times[i]

        depth = 1
        path = (u,)
        path_times = (t,)
        path_amounts = (amount,)
        box = inbox[u]
        if box and amount >= min_amount * MIN_RATIO:
            while box and t - box[0][0] > window_seconds:
                box.popleft()
            best = -1
            best_depth = 0
            for j in range(len(box) - 1, -1, -1):
                received = box[j]
                if received[0] >= t:
                    continue
                if received[1] >= min_amount and MIN_RATIO * received[1] <= amount <= MAX_RATIO * received[1]:
                    if received[2] > best_depth:
                        best_depth = received[2]
                        best = j
            if best >= 0:
                received = box[best]
                del box[best]
                depth = received[2] + 1
                path = (received[3] + (u,))[-MAX_PATH:]
                path_times = (received[4] + (t,))[-MAX_PATH:]
                path_amounts = (received[5] + (amount,))[-MAX_PATH:]
                forward_count[u] += 1
                forwarded_amount[u] += amount
                dwell_sum[u] += t - received[0]
                members = path + (v,)
                for m in members:
                    if depth > chain_length[m]:
                        chain_length[m] = depth
                if v in path:
                    start = path.index(v)
                    loop = path[start:]
                    if len(loop) >= 3:
                        for m in loop:
                            cycle_count[m] += 1
                        if len(cycles) < keep_details:
                            cycles.append({
                                "nodes": list(loop),
                                "length": len(loop),
                                "duration_seconds": float(t - path_times[start]),
                                "first_amount": float(path_amounts[start]),
                                "closing_amount": float(amount),
                            })
                elif depth >= min_chain_hops and len(chains) < keep_details:
                    chains.append({"path": list(members), "hops": int(depth), "end_time": float(t), "amount": float(amount)})

        if amount >= min_amount:
            target = inbox[v]
            if target is None:
                target = inbox[v] = deque(maxlen=MAX_INBOX)
            target.append([t, amount, depth, path, path_times, path_amounts])

    return FlowResult(
        window_seconds=window_seconds,
        forward_count=forward_count,
        forwarded_amount=forwarded_amount,
        chain_length=chain_length,
        cycle_count=cycle_count,
        dwell_sum=dwell_sum,
        cycles=cycles,
        chains=chains,
    )
