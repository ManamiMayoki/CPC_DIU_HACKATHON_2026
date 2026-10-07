"""Phase 2 tests: labelled MFS generator, time-ordered flow tracing, feature store,
trained classifier, tier-aware scoring, rules baseline and the HIGH risk tier."""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "ml"), os.path.join(PROJECT_ROOT, "graph-engine")):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.synthetic.mfs_generator import TYPOLOGIES, generate_mfs_dataset
from data.synthetic.profiles import build_profile, infer_tier
from graph import build_transaction_graph
from ml.evaluation import binary_metrics, rules_baseline
from ml.feature_store import FEATURE_FAMILIES, build_account_features
from ml.inference import run_pipeline
from ml.model import ExplainableRiskScorer
from ml.supervised import ALL_FEATURES, explain_accounts, load_or_train, score_accounts
from ml.temporal_flow import FAST_WINDOW_SECONDS, SLOW_WINDOW_SECONDS, trace_flows
from patterns import detect_temporal_flows, run_all_network_detections

SMALL = {"n_personal": 800, "n_agents": 40, "n_merchants": 50, "fraud_scale": 1.0}
SAMPLE_PATH = os.path.join(PROJECT_ROOT, "data", "synthetic", "transactions_sample.json")


@pytest.fixture(scope="module")
def small_network():
    dataset = generate_mfs_dataset(seed=11, **SMALL)
    tiers = {acc: info["tier"] for acc, info in dataset.accounts.items()}
    return dataset, tiers, build_account_features(dataset.transactions, tiers)


@pytest.fixture(scope="module")
def sample_result():
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        return run_pipeline(json.load(f), contamination=0.10, random_state=42)


def _tx(i, sender, receiver, amount, timestamp):
    return {"transaction_id": f"T{i}", "sender_id": sender, "receiver_id": receiver, "amount": amount, "timestamp": timestamp}


# ------------------------------------------------------------------ generator
def test_generator_is_reproducible_and_labelled():
    a = generate_mfs_dataset(seed=3, **SMALL)
    b = generate_mfs_dataset(seed=3, **SMALL)
    assert a.transactions == b.transactions
    assert a.transactions != generate_mfs_dataset(seed=4, **SMALL).transactions
    summary = a.summary()
    assert set(summary["suspicious_by_typology"]) == set(TYPOLOGIES)
    assert set(summary["accounts_by_tier"]) == {"personal", "agent", "merchant"}
    assert 0 < summary["suspicious_rate"] < 0.5
    stamps = [t["timestamp"] for t in a.transactions]
    assert stamps == sorted(stamps)


def test_generator_can_hold_out_a_typology():
    held = generate_mfs_dataset(seed=3, exclude_typologies=["mule_ring"], **SMALL)
    assert "mule_ring" not in held.summary()["suspicious_by_typology"]


# --------------------------------------------------------------- flow tracing
def test_trace_flows_finds_chain_and_cycle():
    #            A->B      B->C      C->D      D->B (back onto the chain)
    senders = [0, 1, 2, 3]
    receivers = [1, 2, 3, 1]
    amounts = [5000.0, 4900.0, 4800.0, 4700.0]
    times = [0.0, 600.0, 1200.0, 1800.0]
    result = trace_flows(senders, receivers, amounts, times, 4, FAST_WINDOW_SECONDS)
    assert result.chain_length.max() == 4
    assert result.forward_count.tolist() == [0, 1, 1, 1]
    assert result.cycle_count.tolist() == [0, 1, 1, 1]
    assert result.cycles[0]["length"] == 3


def test_trace_flows_respects_window_and_amount():
    # Second hop is 3 hours later: outside the fast window, inside the slow one
    args = ([0, 1], [1, 2], [5000.0, 4900.0], [0.0, 3 * 3600.0], 3)
    assert trace_flows(*args, FAST_WINDOW_SECONDS).forward_count.sum() == 0
    assert trace_flows(*args, SLOW_WINDOW_SECONDS).forward_count.sum() == 1
    # An unrelated small payment is not a forward of the 5,000 received
    unrelated = trace_flows([0, 1], [1, 2], [5000.0, 800.0], [0.0, 600.0], 3, FAST_WINDOW_SECONDS)
    assert unrelated.forward_count.sum() == 0


def test_temporal_detectors_match_exhaustive_search_on_a_simple_loop():
    txs = [
        _tx(1, "A", "B", 5000, "2026-03-01T10:00:00Z"),
        _tx(2, "B", "C", 4900, "2026-03-01T10:10:00Z"),
        _tx(3, "C", "A", 4800, "2026-03-01T10:20:00Z"),
    ]
    graph = build_transaction_graph(txs)
    circular, _ = detect_temporal_flows(graph)
    assert circular.flagged_accounts == ["A", "B", "C"]
    assert circular.details[0]["cycle_path"][0] == circular.details[0]["cycle_path"][-1]
    exhaustive = run_all_network_detections(graph, temporal=False)["circular_flow"]
    assert set(exhaustive.flagged_accounts) == set(circular.flagged_accounts)


# -------------------------------------------------------------- feature store
def test_feature_store_shape_and_families(small_network):
    dataset, _, features = small_network
    assert set(features.columns) == {c for fam in FEATURE_FAMILIES.values() for c in fam}
    assert len(features) == len(dataset.accounts)
    assert np.isfinite(features.values).all()
    assert (features[["tier_personal", "tier_agent", "tier_merchant"]].sum(axis=1) == 1).all()


def test_feature_store_separates_planted_typologies(small_network):
    dataset, _, features = small_network
    typology = np.array([dataset.accounts[a]["typology"] or "none" for a in features.index])
    normal = typology == "none"
    assert features["cycle_count_slow"][typology == "circular_layering"].mean() > 10 * max(features["cycle_count_slow"][normal].mean(), 0.001)
    assert features["chain_length_slow"][typology == "low_slow_mule_chain"].mean() > 2 * features["chain_length_slow"][normal].mean()
    assert features["forward_share_fast"][typology == "mule_ring"].mean() > 5 * features["forward_share_fast"][normal].mean()


def test_feature_store_handles_tiny_input():
    features = build_account_features([_tx(1, "A", "B", 100, "2026-03-01T10:00:00Z")])
    assert set(features.index) == {"A", "B"}
    assert np.isfinite(features.values).all()


# ----------------------------------------------------------------- classifier
def test_classifier_beats_rules_on_an_unseen_network(small_network):
    dataset, _, features = small_network
    labels = np.array([dataset.accounts[a]["label"] for a in features.index])
    bundle = load_or_train()
    assert bundle["features"] == ALL_FEATURES
    scores = score_accounts(features, bundle).values
    model = binary_metrics(labels, scores, scores >= bundle["threshold"])
    rules = rules_baseline(dataset.transactions, features)
    baseline = binary_metrics(labels, rules["score"].values, rules["alert"].values)
    assert model["pr_auc"] > 0.6
    assert model["pr_auc"] > baseline["pr_auc"] + 0.2
    assert model["false_positive_rate"] < baseline["false_positive_rate"]


def test_explanations_name_real_features(small_network):
    _, _, features = small_network
    bundle = load_or_train()
    top = score_accounts(features, bundle).sort_values(ascending=False).index[:3].tolist()
    explained = explain_accounts(features, top, bundle)
    assert set(explained) == set(top)
    for drivers in explained.values():
        assert 1 <= len(drivers) <= 3
        for d in drivers:
            assert d["feature"] in ALL_FEATURES and d["contribution"] >= 0 and d["label"]


# ------------------------------------------------------------ product scoring
def test_demo_data_has_every_risk_tier(sample_result):
    dist = sample_result["risk_distribution"]
    assert all(dist[tier] > 0 for tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
    accounts = {a["account_id"]: a for a in sample_result["accounts"]}
    assert accounts["ACC_MULE_HUB"]["risk_level"] == "CRITICAL"
    assert all(a["risk_level"] == "LOW" for k, a in accounts.items() if k.startswith("ACC_NORM_"))


def test_accounts_carry_classifier_probability_and_drivers(sample_result):
    accounts = {a["account_id"]: a for a in sample_result["accounts"]}
    hub = accounts["ACC_MULE_HUB"]
    assert hub["supervised_probability"] > 0.9
    assert hub["scoring_breakdown"]["supervised_probability"] == hub["supervised_probability"]
    assert hub["model_drivers"] and hub["evidence"][0].startswith("Trained classifier rates this account")
    assert accounts["ACC_NORM_004"]["supervised_probability"] < 0.2
    assert sample_result["models"]["detection_mode"] == "exhaustive graph search"


def test_pipeline_still_works_without_the_classifier():
    with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
        result = run_pipeline(json.load(f), use_supervised=False)
    assert result["pipeline_status"] == "SUCCESS"
    assert all(a["supervised_probability"] is None for a in result["accounts"])


def test_graph_evidence_floor_lifts_corroborated_network_evidence():
    scorer = ExplainableRiskScorer()
    flags = {"circular_flow": True, "rapid_movement": True, "structuring": True, "fan_in": True}
    score, tier, _ = scorer.compute_composite_risk("X", ml_score=5.0, is_ml_anomaly=False, feature_row={}, pattern_flags=flags)
    assert score >= 75.0 and tier == "HIGH"
    quiet, quiet_tier, _ = scorer.compute_composite_risk("Y", ml_score=5.0, is_ml_anomaly=False, feature_row={}, pattern_flags={})
    assert quiet_tier == "LOW" and quiet < 10


def test_business_as_usual_patterns_do_not_count_against_agents():
    scorer = ExplainableRiskScorer()
    flags = {"fan_in": True, "fan_out": True, "rapid_movement": True}
    personal = scorer.compute_composite_risk("P", 10.0, False, {}, flags, account_tier="personal")[2]["graph_component"]
    agent = scorer.compute_composite_risk("A", 10.0, False, {}, flags, account_tier="agent")[2]["graph_component"]
    assert personal == 80.0 and agent == 0.0
    # a circular flow still counts for an agent
    assert scorer.compute_composite_risk("A", 10.0, False, {}, {"circular_flow": True}, account_tier="agent")[2]["graph_component"] == 35.0


def test_large_networks_switch_to_flow_tracing_and_stay_fair_to_agents():
    dataset = generate_mfs_dataset(seed=21, n_personal=2200, n_agents=90, n_merchants=110, fraud_scale=1.0)
    tiers = {acc: info["tier"] for acc, info in dataset.accounts.items()}
    result = run_pipeline(dataset.transactions, contamination=0.05, account_tiers=tiers)
    assert result["models"]["detection_mode"] == "temporal flow tracing"
    legit_agents = [a for a in result["accounts"] if a["account_tier"] == "agent" and dataset.accounts[a["account_id"]]["label"] == 0]
    flagged = sum(a["risk_score"] >= 40 for a in legit_agents)
    assert flagged / len(legit_agents) < 0.15
    suspicious = [a for a in result["accounts"] if dataset.accounts[a["account_id"]]["label"] == 1]
    assert sum(a["risk_score"] >= 40 for a in suspicious) / len(suspicious) > 0.6


# ------------------------------------------------------------------- profiles
def test_profiles_are_deterministic_and_tiered():
    assert build_profile("ACC_X") == build_profile("ACC_X")
    assert infer_tier("ACC_MULE_CASHOUT") == "agent" and infer_tier("ACC_MERCH_0001") == "merchant" and infer_tier("ACC_P_1") == "personal"
    profile = build_profile("ACC_X")
    assert profile["synthetic"] is True and len(profile["phone"]) == 11 and len(profile["national_id"]) == 10


# ------------------------------------------------------------ context detectors
from ml.context_risk import run_context_detectors  # noqa: E402
from ml.validation import validate_transactions  # noqa: E402


def _ctx(i, sender, receiver, amount, timestamp, area, device, tx_type="send_money"):
    return {**_tx(i, sender, receiver, amount, timestamp), "location": area, "device_id": device, "tx_type": tx_type}


def _history(account, area, device, start=0):
    return [_ctx(f"{account}{start + d}", account, "SHOP", 400, f"2026-03-0{d + 1}T10:00:00Z", area, device, "payment") for d in range(4)]


def test_validation_keeps_context_fields():
    raw = [_ctx(1, "A", "B", 100, "2026-03-01T10:00:00Z", "Zone-03", "DEV-1"), _tx(2, "A", "B", 50, "2026-03-01T11:00:00Z")]
    clean = validate_transactions(raw).valid_transactions
    assert clean[0]["location"] == "Zone-03" and clean[0]["device_id"] == "DEV-1" and clean[0]["tx_type"] == "send_money"
    assert "location" not in clean[1]


def test_takeover_needs_a_break_from_the_customers_own_baseline():
    risk = {"Zone-13"}
    txs = (
        _history("VICTIM", "Zone-02", "DEV-V1") + _history("VICTIM2", "Zone-04", "DEV-W1")
        + _history("RESIDENT", "Zone-13", "DEV-R1") + _history("TRAVELLER", "Zone-02", "DEV-T1")
        + [
            # victims: risk area + new handset + large outflow to someone never paid before
            _ctx("v1", "VICTIM", "COLLECTOR", 9000, "2026-03-06T02:00:00Z", "Zone-13", "DEV-STOLEN"),
            _ctx("v2", "VICTIM2", "COLLECTOR", 8000, "2026-03-06T02:30:00Z", "Zone-13", "DEV-STOLEN2"),
            # resident: same area and size of payment, but it is their normal area
            _ctx("r1", "RESIDENT", "COLLECTOR", 9000, "2026-03-06T03:00:00Z", "Zone-13", "DEV-R1"),
            # traveller: risk area, own handset, ordinary small payment to a shop already used
            _ctx("t1", "TRAVELLER", "SHOP", 450, "2026-03-06T12:00:00Z", "Zone-13", "DEV-T1", "payment"),
        ]
    )
    result = run_context_detectors(txs, risk_areas=risk)
    assert result["location_anomaly"]["flagged_accounts"] == ["VICTIM", "VICTIM2"]
    detail = result["location_anomaly"]["details"][0]
    assert detail["usual_areas"] and detail["new_device"] and "new handset" in detail["signals"]
    assert result["takeover_collector"]["flagged_accounts"] == ["COLLECTOR"]
    # no risk areas configured -> nothing is flagged
    assert not run_context_detectors(txs, risk_areas=set())["location_anomaly"]["detected"]


def _hundi(operator, inflow_type, cycles=2, sender="FUNDER"):
    txs = []
    for c in range(cycles):
        day = 2 + 7 * c
        for k in range(3):
            txs.append(_ctx(f"{operator}in{c}{k}", f"{sender}{k % 2}", operator, 20000, f"2026-03-{day:02d}T10:{k}0:00Z", "Zone-05", "D", inflow_type))
        for b in range(6):
            txs.append(_ctx(f"{operator}out{c}{b}", operator, f"{operator}_FAMILY{b}", 9000, f"2026-03-{day:02d}T14:{b}0:00Z", "Zone-05", "D", "cash_in"))
    return txs


def test_hundi_needs_informal_funding_and_recurrence():
    tiers = {"ACC_AGENT_H": "agent", "ACC_AGENT_FORMAL": "agent", "PARTNER0": "merchant", "PARTNER1": "merchant"}
    txs = (
        _hundi("ACC_AGENT_H", "send_money")                                   # informal, recurring -> hundi
        + _hundi("ACC_AGENT_FORMAL", "inward_remittance", sender="PARTNER")   # licensed remittance payout
        + _hundi("ONE_OFF", "send_money", cycles=1, sender="RELATIVE")        # a single family payout
    )
    result = run_context_detectors(txs, tiers)
    assert result["hundi_operator"]["flagged_accounts"] == ["ACC_AGENT_H"]
    detail = result["hundi_operator"]["details"][0]
    assert detail["cycles"] == 2 and detail["beneficiary_count"] == 6 and detail["repeat_beneficiary_share"] == 1.0
    assert result["hundi_funder"]["flagged_accounts"] == ["FUNDER0", "FUNDER1"]
    # beneficiaries are never flagged
    assert not any("FAMILY" in acc for r in result.values() for acc in r["flagged_accounts"])


def test_demo_scenarios_for_hundi_and_takeover(sample_result):
    accounts = {a["account_id"]: a for a in sample_result["accounts"]}
    assert "hundi_operator" in accounts["ACC_HUNDI_AGENT"]["patterns"] and accounts["ACC_HUNDI_AGENT"]["risk_level"] in ("HIGH", "CRITICAL")
    assert accounts["ACC_HUNDI_AGENT"]["investigation"]["typology"].startswith("Hundi operator")
    assert "takeover_collector" in accounts["ACC_TKO_COLLECTOR"]["patterns"] and accounts["ACC_TKO_COLLECTOR"]["risk_score"] >= 70
    for i in (1, 2, 3):
        victim = accounts[f"ACC_TKO_VICTIM_0{i}"]
        assert victim["patterns"] == ["location_anomaly"] and victim["risk_level"] == "MEDIUM"
    assert accounts["ACC_TKO_RESIDENT"]["risk_level"] == "LOW" and not accounts["ACC_TKO_RESIDENT"]["patterns"]
    assert all(accounts[f"ACC_HUNDI_FAMILY_0{i}"]["risk_level"] == "LOW" for i in range(1, 7))
