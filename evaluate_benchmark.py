"""Synthetic Benchmark & Evaluation Runner.

Executes controlled topological benchmark scenarios (NORMAL, FAN_IN, FAN_OUT,
RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK, STRUCTURING, MULE_RING) and prints an explainable,
data-grounded evaluation summary table for hackathon presentation and validation.

DISCLAIMER: This evaluation benchmarks unsupervised pattern detection on controlled
synthetic topologies. It does NOT claim real-world banking accuracy, precision/recall,
or regulatory compliance metrics.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List
import pandas as pd

# Support imports across repo
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (GRAPH_DIR, PROJECT_ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.synthetic.generator import SyntheticDataGenerator
from ml.inference import run_pipeline

# Clearly documented reasonable prototype threshold for false positives in normal baseline
MAX_NORMAL_HIGH_RISK_PCT: float = 15.0  # Max allowable percentage of HIGH+CRITICAL in normal baseline


def evaluate_benchmarks() -> bool:
    """Executes the complete synthetic scenario benchmark suite across all 9 scenarios.

    Returns:
        True if all benchmark criteria pass, False otherwise.
    """
    generator = SyntheticDataGenerator(seed=42)
    print("=" * 110)
    print("CYGNUS AI: SYNTHETIC TOPOLOGY BENCHMARK & RISK SCORING EVALUATION")
    print("=" * 110)
    print("Evaluating unsupervised graph algorithms and explainable ML risk scoring on synthetic topologies.")
    print(f"Parameters: seed=42, random_state=42, contamination=0.10, max_normal_fp_pct={MAX_NORMAL_HIGH_RISK_PCT}%\n")

    # Define all 9 controlled synthetic scenarios (including NORMAL)
    scenarios: List[Dict[str, Any]] = [
        {
            "name": "1. NORMAL",
            "desc": "Baseline peer-to-peer transfers (20 accounts, 80 transactions)",
            "txs": generator.generate_normal_transactions(num_accounts=20, num_transactions=80),
            "is_normal": True,
            "expected_pattern": "No CRITICAL accounts",
            "target_key": None,
        },
        {
            "name": "2. FAN_IN",
            "desc": "Multiple senders funneled to single hub (8 senders -> ACC_FANIN_HUB)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_fan_in_scenario(target_account="ACC_FANIN_HUB", num_senders=8),
            "is_normal": False,
            "expected_pattern": "fan_in",
            "target_key": "ACC_FANIN_HUB",
        },
        {
            "name": "3. FAN_OUT",
            "desc": "Single distributor dispersing to multiple accounts (ACC_FANOUT_HUB -> 8 receivers)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_fan_out_scenario(source_account="ACC_FANOUT_HUB", num_receivers=8),
            "is_normal": False,
            "expected_pattern": "fan_out",
            "target_key": "ACC_FANOUT_HUB",
        },
        {
            "name": "4. RAPID_MOVEMENT",
            "desc": "Pass-through intermediary (ACC_RAPID_IN -> ACC_RAPID_MID -> ACC_RAPID_OUT within 5 min)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_rapid_movement_scenario(intermediary_account="ACC_RAPID_MID"),
            "is_normal": False,
            "expected_pattern": "rapid_movement",
            "target_key": "ACC_RAPID_MID",
        },
        {
            "name": "5. CHAIN",
            "desc": "Multi-hop linear forwarding (5 accounts, 4 hops: ACC_CHAIN_00 to 04)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_chain_scenario(chain_length=5, prefix="ACC_CHAIN"),
            "is_normal": False,
            "expected_pattern": "transaction_chain",
            "target_key": "ACC_CHAIN_02",
        },
        {
            "name": "6. CIRCULAR_FLOW",
            "desc": "Directed cycle (ACC_CYCLE_A -> B -> C -> A)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_circular_flow_scenario(cycle_nodes=["ACC_CYCLE_A", "ACC_CYCLE_B", "ACC_CYCLE_C"]),
            "is_normal": False,
            "expected_pattern": "circular_flow",
            "target_key": "ACC_CYCLE_A",
        },
        {
            "name": "7. COORDINATED_NETWORK",
            "desc": "Dense interlocking cluster (5 accounts: ACC_COORD_00 to 04)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_coordinated_network_scenario(network_size=5, prefix="ACC_COORD"),
            "is_normal": False,
            "expected_pattern": "coordinated_network",
            "target_key": "ACC_COORD_00",
        },
        {
            "name": "8. STRUCTURING",
            "desc": "5 transfers just under the 10,000 threshold (ACC_STRUCT_SRC -> ACC_STRUCT_DST)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_structuring_scenario(),
            "is_normal": False,
            "expected_pattern": "structuring",
            "target_key": "ACC_STRUCT_SRC",
        },
        {
            "name": "9. MULE_RING",
            "desc": "Feeders -> hub -> mules -> cash-out agent -> hub (combined typologies)",
            "txs": generator.generate_normal_transactions(num_accounts=10, num_transactions=20)
                   + generator.generate_mule_ring_scenario(),
            "is_normal": False,
            "expected_pattern": "structuring",
            "target_key": "ACC_MULE_HUB",
        },
    ]

    scenario_rows: List[Dict[str, Any]] = []
    pattern_passes = 0
    target_risk_passes = 0
    total_non_normal = 0
    normal_passes = False
    normal_fp_summary = ""

    for sc in scenarios:
        res = run_pipeline(sc["txs"], random_state=42)
        total_accs = res["total_accounts_analyzed"]
        dist = res["risk_distribution"]

        if sc["is_normal"]:
            # NORMAL scenario evaluation: count HIGH, CRITICAL, and high-risk percentage
            n_high = dist.get("HIGH", 0)
            n_crit = dist.get("CRITICAL", 0)
            high_crit_pct = ((n_high + n_crit) / total_accs * 100.0) if total_accs > 0 else 0.0

            # Pass criterion: zero CRITICAL accounts and high-risk rate within threshold
            normal_passes = (n_crit == 0) and (high_crit_pct <= MAX_NORMAL_HIGH_RISK_PCT)
            sc_status = "PASS" if normal_passes else "FAIL"

            reason = f"{n_crit} CRITICAL, {n_high} HIGH ({high_crit_pct:.1f}% <= {MAX_NORMAL_HIGH_RISK_PCT}% limit)"
            normal_fp_summary = f"{n_crit} CRITICAL, {n_high} HIGH ({high_crit_pct:.1f}% of {total_accs} accounts)"

            scenario_rows.append({
                "Scenario": sc["name"],
                "Target Account": "ALL (Normal Baseline)",
                "Expected Pattern": sc["expected_pattern"],
                "Pattern Detected": "YES (0 CRITICAL)" if n_crit == 0 else "NO (Has CRITICAL)",
                "Target Score": f"FP Rate: {high_crit_pct:.1f}%",
                "Target Tier": f"{dist.get('LOW', 0)}L/{dist.get('MEDIUM', 0)}M/{n_high}H/{n_crit}C",
                "Target Anomaly": f"{n_crit} Crit",
                "Status": sc_status,
                "Evaluation Reason": reason,
            })
        else:
            total_non_normal += 1
            target_acc = next((a for a in res["accounts"] if a["account_id"] == sc["target_key"]), None)

            if target_acc:
                pats = target_acc.get("patterns", [])
                pat_detected = sc["expected_pattern"] in pats
                r_score = target_acc.get("risk_score", 0.0)
                r_level = target_acc.get("risk_level", "LOW")
                is_anomaly = target_acc.get("is_anomaly", False)

                # Target account evaluation: pattern detected and risk score elevated (>= 40.0)
                score_elevated = r_score >= 40.0
                if pat_detected:
                    pattern_passes += 1
                if score_elevated:
                    target_risk_passes += 1

                sc_passed = pat_detected and score_elevated
                sc_status = "PASS" if sc_passed else "FAIL"

                if sc_passed:
                    reason = f"Pattern '{sc['expected_pattern']}' detected; risk score {r_score:.2f} >= 40.0"
                elif not pat_detected:
                    reason = f"Pattern '{sc['expected_pattern']}' not detected in {pats}"
                else:
                    reason = f"Risk score {r_score:.2f} was not elevated (< 40.0)"
            else:
                pat_detected = False
                r_score = 0.0
                r_level = "MISSING"
                is_anomaly = False
                sc_status = "FAIL"
                reason = f"Target account {sc['target_key']} not found in pipeline output"

            scenario_rows.append({
                "Scenario": sc["name"],
                "Target Account": sc["target_key"],
                "Expected Pattern": sc["expected_pattern"],
                "Pattern Detected": "YES" if pat_detected else "NO",
                "Target Score": f"{r_score:.2f}",
                "Target Tier": r_level,
                "Target Anomaly": "TRUE" if is_anomaly else "FALSE",
                "Status": sc_status,
                "Evaluation Reason": reason,
            })

    # Print Clean Presentation Table
    print("BENCHMARK SCENARIO EVALUATION RESULTS:")
    df_results = pd.DataFrame(scenario_rows)
    print(df_results.to_string(index=False))
    print("\n" + "=" * 110)

    # Overall Summary
    all_patterns_passed = (pattern_passes == total_non_normal)
    all_targets_elevated = (target_risk_passes == total_non_normal)
    all_7_passed = normal_passes and all_patterns_passed and all_targets_elevated

    print("OVERALL BENCHMARK SUMMARY:")
    print(f" - Pattern Detection Pass Count:       {pattern_passes} / {total_non_normal} non-normal scenarios ({'PASS' if all_patterns_passed else 'FAIL'})")
    print(f" - Target-Account High-Risk Pass Count: {target_risk_passes} / {total_non_normal} targets elevated (Score >= 40.0) ({'PASS' if all_targets_elevated else 'FAIL'})")
    print(f" - Normal Baseline False-Positive Count: {normal_fp_summary} ({'PASS' if normal_passes else 'FAIL'})")
    print(f" - Total Scenarios Passing:            {sum(1 for r in scenario_rows if r['Status'] == 'PASS')} / {len(scenarios)}")
    print("=" * 110)

    if all_7_passed:
        print("OVERALL BENCHMARK VERDICT: [PASS] - ALL SCENARIOS SATISFIED BENCHMARK CRITERIA")
        print("=" * 110)
        return True
    else:
        print("OVERALL BENCHMARK VERDICT: [FAIL] - ONE OR MORE SCENARIOS FAILED BENCHMARK CRITERIA")
        print("=" * 110)
        return False


def main() -> None:
    passed = evaluate_benchmarks()
    # Requirement 5: Exit with non-zero status code when benchmark fails
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
