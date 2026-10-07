"""Context detectors: risk-area account takeover and hundi (informal remittance) networks.

Both work on the transaction stream itself, using optional context fields
(`location`, `device_id`, `tx_type`) when the data has them. Both are built around the same
rule: compare behaviour with the account's own history, so ordinary customers are left alone.

1. Risk-area account takeover
   Stolen or compromised handsets are often moved to a few areas and emptied there. A
   customer whose wallet suddenly transacts from a listed risk area is NOT flagged for that
   alone. The alert needs at least two independent signals, measured against the customer's
   own baseline: the area is new for this customer, the handset is new, and the money leaves
   unusually fast, mostly to receivers the customer never paid before. Customers who live or
   regularly transact in a risk area have it in their baseline and are never flagged by it.
   The wallet that collects from several such customers is flagged as the takeover collector.
   The alert on the customer's wallet is a protective one (step-up authentication, call the
   customer), not a suspicion of the customer.

2. Hundi (informal remittance) network
   In hundi, money sent from abroad never enters Bangladesh through a licensed channel. A
   local funder pays an operator, very often an agent wallet, who pays out to the families.
   On the wallet it looks like: a few funders sending large informal transfers, followed
   within hours by remittance-sized payouts to a set of beneficiaries, and the same
   beneficiaries paid again cycle after cycle. Formal inward remittance and distributor float
   are excluded, so an agent doing licensed remittance payout is not flagged. Beneficiaries
   are listed as related accounts, never flagged.

All thresholds are prototype settings for synthetic data. The risk-area list is configuration
(data/config/risk_areas.json), not code.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set

from ml.validation import parse_iso_timestamp

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
RISK_AREA_CONFIG = os.path.join(PROJECT_ROOT, "data", "config", "risk_areas.json")

# --- risk-area takeover settings
MIN_HISTORY = 3                 # located transactions needed before a baseline exists
USUAL_AREA_SHARE = 0.10         # an area with at least this share of past activity is "usual"
EPISODE_SECONDS = 24 * 3600.0
DRAIN_MULTIPLE = 3.0            # outflow vs the customer's typical active-day outflow
DRAIN_MIN_AMOUNT = 5000.0
TAKEOVER_ALERT_SCORE = 30       # needs at least two signals
MIN_VICTIMS_FOR_COLLECTOR = 2

# --- hundi settings
FORMAL_TX_TYPES = {"inward_remittance", "float_topup", "float_return", "salary", "settlement", "cash_out", "payment"}
INFORMAL_MIN_AMOUNT = 10000.0
MIN_INFORMAL_INFLOWS = 3
MIN_INFORMAL_TOTAL = 50000.0
MAX_FUNDERS = 6
PAYOUT_WINDOW_SECONDS = 24 * 3600.0
PAYOUT_MIN, PAYOUT_MAX = 3000.0, 50000.0
MIN_BENEFICIARIES = 5
MIN_PAYOUT_RATIO = 0.6
CYCLE_GAP_SECONDS = 3 * 86400.0
MIN_CYCLES = 2
MIN_REPEAT_SHARE = 0.4

CONTEXT_PATTERNS = ("location_anomaly", "takeover_collector", "hundi_operator", "hundi_funder")


def load_risk_areas(path: str = RISK_AREA_CONFIG) -> Set[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {str(a) for a in json.load(f).get("risk_areas", [])}
    except (OSError, ValueError):
        return set()


def _rows(transactions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for tx in transactions:
        dt = parse_iso_timestamp(tx.get("timestamp"))
        if dt is None:
            continue
        rows.append({
            "t": dt.timestamp(),
            "when": dt.isoformat(),
            "sender": str(tx.get("sender_id") or tx.get("sender")),
            "receiver": str(tx.get("receiver_id") or tx.get("receiver")),
            "amount": float(tx.get("amount", 0.0)),
            "tx_type": tx.get("tx_type"),
            "location": tx.get("location"),
            "device": tx.get("device_id"),
        })
    rows.sort(key=lambda r: r["t"])
    return rows


def _result(name: str, details: List[Dict[str, Any]], description: str) -> Dict[str, Any]:
    flagged = sorted({d["account_id"] for d in details})
    return {"detected": bool(flagged), "flagged_accounts": flagged, "count": len(flagged), "description": description, "details": details}


# ------------------------------------------------------------- risk-area account takeover
def detect_location_takeover(rows: List[Dict[str, Any]], risk_areas: Set[str]) -> Dict[str, Dict[str, Any]]:
    by_sender: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_sender[row["sender"]].append(row)

    victim_details: List[Dict[str, Any]] = []
    collected: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"victims": set(), "amount": 0.0, "areas": set()})

    for account, sent in by_sender.items():
        if not risk_areas or not any(r["location"] in risk_areas for r in sent):
            continue
        area_counts: Dict[str, int] = defaultdict(int)
        devices: Set[str] = set()
        paid_before: Set[str] = set()
        daily_out: Dict[int, float] = defaultdict(float)
        located = 0
        episode_end = -1.0
        flagged_until = -1.0
        for i, row in enumerate(sent):
            area = row["location"]
            in_episode = row["t"] <= episode_end
            unusual = (
                area in risk_areas and located >= MIN_HISTORY
                and area_counts[area] / located < USUAL_AREA_SHARE
            )
            if unusual and not in_episode:
                window = [r for r in sent[i:] if r["t"] - row["t"] <= EPISODE_SECONDS and r["location"] == area]
                outflow = sum(r["amount"] for r in window)
                to_new = sum(r["amount"] for r in window if r["receiver"] not in paid_before)
                typical_day = statistics.median(daily_out.values()) if daily_out else 0.0
                new_device = bool(row["device"]) and bool(devices) and row["device"] not in devices
                drain = outflow >= max(DRAIN_MULTIPLE * typical_day, DRAIN_MIN_AMOUNT)
                mostly_new_receivers = outflow > 0 and to_new / outflow >= 0.5
                score = 15 + 15 * new_device + 15 * drain + 10 * mostly_new_receivers
                if score >= TAKEOVER_ALERT_SCORE:
                    signals = ["first activity from this risk area"]
                    if new_device:
                        signals.append("new handset")
                    if drain:
                        signals.append("unusually large outflow in 24 hours")
                    if mostly_new_receivers:
                        signals.append("money sent to receivers never paid before")
                    receivers = sorted({r["receiver"] for r in window})
                    victim_details.append({
                        "account_id": account,
                        "risk_area": area,
                        "usual_areas": sorted(a for a, c in area_counts.items() if c / located >= USUAL_AREA_SHARE),
                        "new_device": new_device,
                        "first_seen": row["when"],
                        "outflow_24h": round(outflow, 2),
                        "typical_daily_outflow": round(typical_day, 2),
                        "transactions": len(window),
                        "signals": signals,
                        "signal_score": int(score),
                        "receivers": receivers,
                    })
                    flagged_until = row["t"] + EPISODE_SECONDS
                    for r in window:
                        if r["receiver"] not in paid_before:
                            bucket = collected[r["receiver"]]
                            bucket["victims"].add(account)
                            bucket["amount"] += r["amount"]
                            bucket["areas"].add(area)
                episode_end = row["t"] + EPISODE_SECONDS
            # Activity inside a flagged takeover must not become part of the baseline. Unflagged
            # visits do, so a customer who travels or moves there builds a new normal.
            if not (row["t"] <= flagged_until and area in risk_areas):
                if area:
                    area_counts[area] += 1
                    located += 1
                if row["device"]:
                    devices.add(row["device"])
                paid_before.add(row["receiver"])
                daily_out[int(row["t"] // 86400)] += row["amount"]

    collector_details = [
        {
            "account_id": receiver,
            "victim_count": len(info["victims"]),
            "victims": sorted(info["victims"]),
            "amount_collected": round(info["amount"], 2),
            "risk_areas": sorted(info["areas"]),
        }
        for receiver, info in collected.items() if len(info["victims"]) >= MIN_VICTIMS_FOR_COLLECTOR
    ]
    return {
        "location_anomaly": _result(
            "location_anomaly", victim_details,
            f"{len(victim_details)} wallet(s) suddenly active from a listed risk area with at least two takeover signals.",
        ),
        "takeover_collector": _result(
            "takeover_collector", collector_details,
            f"{len(collector_details)} wallet(s) collecting from {MIN_VICTIMS_FOR_COLLECTOR}+ wallets during suspected takeovers.",
        ),
    }


# ------------------------------------------------------------------------- hundi networks
def detect_hundi_networks(rows: List[Dict[str, Any]], tiers: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    tiers = tiers or {}
    inflows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    outflows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        formal = row["tx_type"] in FORMAL_TX_TYPES or tiers.get(row["sender"], "personal") == "merchant"
        if row["amount"] >= INFORMAL_MIN_AMOUNT and not formal:
            inflows[row["receiver"]].append(row)
        if PAYOUT_MIN <= row["amount"] <= PAYOUT_MAX and row["tx_type"] not in ("float_return", "settlement", "payment") \
                and tiers.get(row["receiver"], "personal") == "personal":
            outflows[row["sender"]].append(row)

    operator_details: List[Dict[str, Any]] = []
    funder_details: List[Dict[str, Any]] = []
    for account, informal in inflows.items():
        funders = {r["sender"] for r in informal}
        total_in = sum(r["amount"] for r in informal)
        if len(informal) < MIN_INFORMAL_INFLOWS or total_in < MIN_INFORMAL_TOTAL or len(funders) > MAX_FUNDERS:
            continue
        # Split the funding into cycles separated by quiet gaps
        cycles: List[List[Dict[str, Any]]] = [[informal[0]]]
        for row in informal[1:]:
            if row["t"] - cycles[-1][-1]["t"] >= CYCLE_GAP_SECONDS:
                cycles.append([row])
            else:
                cycles[-1].append(row)
        payouts_by_cycle: List[List[Dict[str, Any]]] = []
        for cycle in cycles:
            start, end = cycle[0]["t"], cycle[-1]["t"] + PAYOUT_WINDOW_SECONDS
            payouts_by_cycle.append([
                r for r in outflows.get(account, [])
                if start <= r["t"] <= end and r["receiver"] not in funders
            ])
        payouts = [r for cycle in payouts_by_cycle for r in cycle]
        beneficiaries = {r["receiver"] for r in payouts}
        total_out = sum(r["amount"] for r in payouts)
        if len(beneficiaries) < MIN_BENEFICIARIES or total_out < MIN_PAYOUT_RATIO * total_in:
            continue
        paid_cycles: Dict[str, int] = defaultdict(int)
        for cycle in payouts_by_cycle:
            for b in {r["receiver"] for r in cycle}:
                paid_cycles[b] += 1
        active_cycles = sum(1 for cycle in payouts_by_cycle if cycle)
        repeat_share = sum(1 for n in paid_cycles.values() if n >= 2) / len(beneficiaries)
        if active_cycles < MIN_CYCLES or repeat_share < MIN_REPEAT_SHARE:
            continue  # one-off payouts (a wedding, a land sale) are not a hundi operation
        delays = []
        for cycle, cycle_payouts in zip(cycles, payouts_by_cycle):
            delays += [(r["t"] - cycle[0]["t"]) / 3600.0 for r in cycle_payouts]
        operator_details.append({
            "account_id": account,
            "account_tier": tiers.get(account, "personal"),
            "funders": sorted(funders),
            "informal_inflow_count": len(informal),
            "informal_inflow_total": round(total_in, 2),
            "beneficiary_count": len(beneficiaries),
            "beneficiaries": sorted(beneficiaries),
            "payout_total": round(total_out, 2),
            "payout_ratio": round(total_out / total_in, 3),
            "cycles": active_cycles,
            "repeat_beneficiary_share": round(repeat_share, 3),
            "median_payout_delay_hours": round(statistics.median(delays), 2) if delays else None,
        })
        for funder in sorted(funders):
            sent = [r for r in informal if r["sender"] == funder]
            funder_details.append({
                "account_id": funder,
                "operator": account,
                "transfers": len(sent),
                "amount": round(sum(r["amount"] for r in sent), 2),
            })
    return {
        "hundi_operator": _result(
            "hundi_operator", operator_details,
            f"{len(operator_details)} wallet(s) repeatedly paying out informal large inflows to a stable set of beneficiaries.",
        ),
        "hundi_funder": _result(
            "hundi_funder", funder_details,
            f"{len(funder_details)} wallet(s) funding a suspected hundi operator.",
        ),
    }


def run_context_detectors(
    transactions: Iterable[Dict[str, Any]],
    tiers: Optional[Dict[str, str]] = None,
    risk_areas: Optional[Set[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    rows = _rows(transactions)
    results = detect_location_takeover(rows, load_risk_areas() if risk_areas is None else set(risk_areas))
    results.update(detect_hundi_networks(rows, tiers))
    return results
