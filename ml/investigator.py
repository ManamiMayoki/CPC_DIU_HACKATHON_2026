"""AI Investigator: deterministic case briefing built from an account's computed evidence.

Every statement here is derived from metrics and pattern details the pipeline calculated
for the account. Nothing is invented. The backend can optionally ask an LLM to rewrite this
briefing as a narrative; this module is the offline fallback and the grounding for that call.

DISCLAIMER: Briefings support investigation prioritization on synthetic data. They do NOT
prove financial crime and are not regulatory determinations.
"""

from __future__ import annotations

from typing import Any, Dict, List

PATTERN_LABELS = {
    "fan_in": "fan-in collection",
    "fan_out": "fan-out dispersal",
    "rapid_movement": "rapid pass-through",
    "transaction_chain": "multi-hop chain",
    "circular_flow": "circular flow",
    "structuring": "structuring",
    "coordinated_network": "coordinated cluster",
    "location_anomaly": "risk-area activity outside the customer's baseline",
    "takeover_collector": "collection from suspected takeovers",
    "hundi_operator": "hundi-style recurring payout",
    "hundi_funder": "funding of a hundi operator",
}

# Ordered most to least specific; the first match names the case typology.
TYPOLOGIES = [
    ({"hundi_operator"}, "Hundi operator (informal remittance payout)",
     "repeatedly receives large informal transfers from a few funders and pays them out to the same beneficiaries, outside licensed remittance channels"),
    ({"hundi_funder"}, "Hundi funder",
     "repeatedly sends large transfers to a wallet that pays them out as informal remittance"),
    ({"takeover_collector"}, "Account-takeover collector",
     "collects money from several wallets that were suddenly emptied from a risk area"),
    ({"location_anomaly"}, "Possible account takeover (customer at risk)",
     "was suddenly used from a risk area, outside this customer's normal pattern, to move money out fast"),
    ({"fan_in", "rapid_movement", "structuring"}, "Money-mule collection hub",
     "collects split deposits from many wallets and forwards them almost immediately"),
    ({"structuring", "fan_in"}, "Structured deposit collection",
     "receives many near-threshold deposits from different wallets"),
    ({"structuring"}, "Structuring (smurfing)",
     "moves money in repeated amounts kept just under the monitoring threshold"),
    ({"circular_flow", "rapid_movement"}, "Layering loop",
     "passes funds quickly around a loop that returns them to their origin"),
    ({"circular_flow"}, "Round-tripping",
     "sends funds around a closed loop that brings most of the value back"),
    ({"coordinated_network"}, "Coordinated account cluster",
     "transacts densely with a closed group of wallets"),
    ({"rapid_movement", "transaction_chain"}, "Pass-through mule",
     "relays funds along a multi-hop chain within minutes"),
    ({"rapid_movement"}, "Pass-through account",
     "forwards most incoming funds onward within the hour"),
    ({"fan_out"}, "Dispersal account",
     "spreads funds to many receivers in a short burst"),
    ({"fan_in"}, "Collection account",
     "receives funds from many different senders in a short burst"),
    ({"transaction_chain"}, "Chain intermediary",
     "sits inside a multi-hop transfer chain"),
]

NEXT_STEPS = {
    "structuring": [
        "Pull the full list of near-threshold transfers and check whether one person controls the sending wallets (same NID, device or SIM).",
        "Compare the combined amount with the account's declared income or business profile.",
    ],
    "fan_in": [
        "Identify the sending wallets and check how recently they were opened and whether they share a device, SIM or agent.",
        "Contact a sample of senders to confirm the purpose of their payments.",
    ],
    "fan_out": [
        "Trace where the receiving wallets sent the money next and whether they cashed out through the same agents.",
    ],
    "rapid_movement": [
        "Review the timing of each receive-and-forward pair; funds held for minutes suggest the wallet is a relay, not the beneficiary.",
        "Check cash-out records for the destination wallets and the agents involved.",
    ],
    "circular_flow": [
        "Map every hop in the loop and confirm whether the wallets share an owner or beneficiary.",
        "Look for a business reason for money returning to its origin; absent one, treat it as layering.",
    ],
    "transaction_chain": [
        "Follow the chain to its final destination wallet and review that wallet's cash-out activity.",
    ],
    "location_anomaly": [
        "Treat the customer as a possible victim: trigger step-up authentication (PIN reset, OTP to the registered SIM) and call the registered number.",
        "Check for a recent SIM replacement or device change on the wallet and consider a temporary hold on outgoing transfers under upay policy.",
        "If the customer confirms the activity is theirs, close as a false positive; the area then becomes part of their normal pattern.",
    ],
    "takeover_collector": [
        "Hold outgoing transfers and cash-out on the collecting wallet under internal policy and review its KYC, device and agent linkage.",
        "List every wallet that paid it during the suspected takeovers and contact those customers.",
    ],
    "hundi_operator": [
        "Compare the payouts with licensed inward-remittance records; payouts with no matching formal remittance indicate hundi.",
        "Interview the agent or wallet owner about the source of the large transfers and review the funders' KYC and income profile.",
        "Check whether the same beneficiaries are paid on a monthly cycle and whether they have relatives working abroad.",
    ],
    "hundi_funder": [
        "Establish the source of the funds sent to the operator and whether the funder is linked to an overseas hundi network.",
    ],
    "coordinated_network": [
        "Review the cluster's KYC records together: shared addresses, devices, SIMs or registration agents point to common control.",
    ],
}

CLOSING_STEPS = {
    "CRITICAL": "Escalate to the compliance officer today; consider a temporary hold on outgoing transfers under internal policy and prepare a Suspicious Transaction Report (STR) for BFIU if the review confirms the pattern.",
    "HIGH": "Escalate for priority review and decide on enhanced due diligence or an STR once the checks above are complete.",
    "MEDIUM": "Place the account on enhanced monitoring and review again if similar activity repeats.",
    "LOW": "The score is below the review threshold, so keep the account on routine monitoring; the checks above apply only if the pattern repeats.",
}


def _money(value: Any) -> str:
    try:
        return f"BDT {float(value):,.0f}"
    except (TypeError, ValueError):
        return "BDT 0"


def _related_accounts(account_id: str, pattern_details: Dict[str, Any]) -> List[str]:
    related: List[str] = []
    for detail in pattern_details.values():
        for key in ("senders", "receivers", "nodes", "chain_path", "accounts", "counterparties", "victims", "funders", "beneficiaries"):
            for acc in detail.get(key, []) or []:
                if acc != account_id and acc not in related:
                    related.append(acc)
        for match in detail.get("matches", []) or []:
            for acc in (match.get("incoming_from"), match.get("outgoing_to")):
                if acc and acc != account_id and acc not in related:
                    related.append(acc)
    return related


def _degree_sentence(prefix: str, degree: int, burst: Any) -> str:
    if not burst:
        return f"{prefix} {degree} different wallets."
    if burst >= degree:
        return f"{prefix} {degree} different wallets, all within two hours."
    return f"{prefix} {degree} different wallets, {burst} of them within two hours."


def _findings(features: Dict[str, Any], patterns: List[str], details: Dict[str, Any]) -> List[str]:
    findings: List[str] = []
    if "structuring" in patterns:
        s = details.get("structuring", {})
        verb = "Sent" if s.get("role") == "splitter" else "Received"
        findings.append(
            f"{verb} {s.get('near_threshold_count', 'several')} transfers just under {_money(s.get('reporting_threshold', 10000))}, "
            f"totalling {_money(s.get('total_amount', 0))} within 24 hours."
        )
    if "fan_in" in patterns:
        f = details.get("fan_in", {})
        burst = f.get("max_senders_in_burst_window")
        findings.append(_degree_sentence("Received money from", int(features.get("in_degree", 0)), burst))
    if "fan_out" in patterns:
        f = details.get("fan_out", {})
        burst = f.get("max_receivers_in_burst_window")
        findings.append(_degree_sentence("Sent money to", int(features.get("out_degree", 0)), burst))
    if "rapid_movement" in patterns:
        r = details.get("rapid_movement", {})
        matches = r.get("matches", [])
        latency = r.get("fastest_latency_seconds")
        when = "under a minute" if latency is not None and latency < 60 else f"{round((latency or 0) / 60)} minutes"
        forwards = {(m.get("outgoing_to"), m.get("outgoing_time")) for m in matches}
        destinations = {m.get("outgoing_to") for m in matches if m.get("outgoing_to")}
        times = "once" if len(forwards) == 1 else f"{len(forwards)} times"
        findings.append(
            f"Passed received money straight on {times} (to {len(destinations)} wallet{'s' if len(destinations) != 1 else ''}), "
            f"the fastest within {when} of receipt."
        )
    if "circular_flow" in patterns:
        c = details.get("circular_flow", {})
        if c.get("cycle_path"):
            findings.append(
                f"Money went around the loop {' -> '.join(c['cycle_path'])} in "
                f"{round(c.get('loop_duration_seconds', 0) / 60)} minutes and {round(c.get('amount_retained_ratio', 0) * 100)}% of it came back."
            )
    if "transaction_chain" in patterns and features.get("chain_length", 0):
        findings.append(f"Part of a transfer chain spanning {int(features['chain_length'])} hops.")
    if "coordinated_network" in patterns:
        c = details.get("coordinated_network", {})
        findings.append(
            f"Member of a closed cluster of {c.get('size', 'several')} wallets with internal density {c.get('density', 'high')}."
        )
    passthrough = features.get("passthrough_ratio", 0.0)
    if passthrough >= 0.85 and features.get("total_incoming", 0.0) > 1000:
        findings.append(f"Passed on {round(passthrough * 100)}% of everything it received, keeping almost nothing.")
    return findings


def build_investigation(report: Dict[str, Any], features: Dict[str, Any], pattern_details: Dict[str, Any]) -> Dict[str, Any]:
    """Builds a grounded case briefing for one account report from run_pipeline."""
    account_id = report["account_id"]
    patterns = list(report.get("patterns", []))
    level = report.get("risk_level", "LOW")
    score = report.get("risk_score", 0.0)
    breakdown = report.get("scoring_breakdown", {})

    typology, typology_text = "No suspicious typology", "shows no network pattern that matches a known typology"
    for required, name, text in TYPOLOGIES:
        if required.issubset(patterns):
            typology, typology_text = name, text
            break

    findings = _findings(features, patterns, pattern_details)
    if report.get("is_anomaly"):
        findings.append(
            f"The Isolation Forest model ranks its overall behaviour as a statistical outlier (ML score {breakdown.get('ml_component', 0):.0f}/100)."
        )

    related = _related_accounts(account_id, pattern_details)

    if patterns:
        pattern_names = ", ".join(PATTERN_LABELS.get(p, p) for p in patterns)
        summary = (
            f"{account_id} scores {score:.1f}/100 ({level}). It {typology_text}. "
            f"Detected patterns: {pattern_names}. "
            f"Received {_money(features.get('total_incoming', 0))} and sent {_money(features.get('total_outgoing', 0))} "
            f"across {int(features.get('transaction_count', 0))} transactions."
        )
    else:
        summary = (
            f"{account_id} scores {score:.1f}/100 ({level}). No network pattern was detected; "
            f"{int(features.get('transaction_count', 0))} transactions look like ordinary activity."
        )
        if report.get("is_anomaly"):
            summary += " The ML model still ranks it as an outlier, so a quick manual look is worthwhile."

    steps: List[str] = []
    for pattern in ("hundi_operator", "hundi_funder", "takeover_collector", "location_anomaly", "structuring", "fan_in", "rapid_movement", "circular_flow", "fan_out", "transaction_chain", "coordinated_network"):
        if pattern in patterns:
            for step in NEXT_STEPS[pattern]:
                if step not in steps:
                    steps.append(step)
    steps = steps[:5]
    if related and level in ("MEDIUM", "HIGH", "CRITICAL"):
        steps.append(f"Open linked cases for {', '.join(related[:4])}{' and others' if len(related) > 4 else ''} in Follow the Money.")
    steps.append(CLOSING_STEPS.get(level, CLOSING_STEPS["LOW"]))

    return {
        "account_id": account_id,
        "headline": f"{typology}: {account_id}" if patterns else f"Routine activity: {account_id}",
        "typology": typology,
        "summary": summary,
        "key_findings": findings,
        "next_steps": steps,
        "related_accounts": related[:12],
        "caveat": "Generated from synthetic data and computed metrics. These are risk indicators for prioritisation, not proof of wrongdoing.",
        "generated_by": "rule-based",
    }
