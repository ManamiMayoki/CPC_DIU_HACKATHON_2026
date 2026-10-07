"""Phase 2 model evaluation on the large labelled synthetic MFS network.

Compares, on held-out networks the models never saw:

  rules_baseline       conventional per-account monitoring rules (no graph)
  phase1_composite     the Phase 1 Cygnus score (static-graph detectors + IsolationForest)
  graph_detectors      the 7 graph pattern detectors alone, with time-ordered flow tracing
  isolation_forest     unsupervised anomaly detection on the full feature store
  cygnus_composite     the current product score (graph + classifier/IsolationForest + behaviour)
  gbm_tabular          supervised gradient boosting, transactional + temporal features only
  rf_graph             supervised random forest, all features incl. graph + neighbourhood
  gbm_graph            supervised gradient boosting, all features (reference model)

and reports precision, recall, F1, PR-AUC, ROC-AUC and false-positive rate, recall per
typology, a feature-family ablation, permutation feature importance, a leave-one-typology-out
test (can the model catch a typology it was never trained on?), a bias check across account
tiers and districts, and an analyst-workload estimate.

Run:  python -m ml.evaluation            (about 10 minutes)
      python -m ml.evaluation --quick    (small networks, for tests)

Writes docs/evaluation/phase2_results.json, frontend/public/data/evaluation.json and
docs/PHASE2_METRICS.md. All numbers in the docs come from this file's output.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
GRAPH_DIR = os.path.join(PROJECT_ROOT, "graph-engine")
for p in (PROJECT_ROOT, GRAPH_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.synthetic.mfs_generator import THRESHOLD, TYPOLOGIES, TYPOLOGY_LABELS, generate_mfs_dataset  # noqa: E402
from ml.feature_store import FEATURE_FAMILIES, build_account_features, feature_family, transactions_to_frame  # noqa: E402
from ml.context_risk import run_context_detectors  # noqa: E402
from ml.inference import run_pipeline  # noqa: E402
from ml.model import AnomalyDetector  # noqa: E402
from ml.supervised import (  # noqa: E402
    ALL_FEATURES, EVAL_SIZE, TABULAR_FEATURES, TRAIN_SEEDS, VALIDATION_SEED,
    best_f1_threshold, make_gbm, make_random_forest,
)

TEST_SEEDS = (101, 202, 303)
QUICK_SIZE = {"n_personal": 1500, "n_agents": 60, "n_merchants": 80, "fraud_scale": 1.0}
ANALYST_MINUTES_PER_ALERT = 20  # stated assumption for the workload estimate, not a measurement

MODEL_LABELS = {
    "rules_baseline": "Rules only (conventional monitoring)",
    "phase1_composite": "Phase 1 Cygnus score",
    "graph_detectors": "Graph pattern detectors",
    "isolation_forest": "IsolationForest (unsupervised)",
    "cygnus_composite": "Cygnus composite score (current product)",
    "gbm_tabular": "Gradient boosting, no graph features",
    "rf_graph": "Random forest + graph features",
    "gbm_graph": "Gradient boosting + graph features",
}
MODEL_KIND = {
    "rules_baseline": "rules", "phase1_composite": "unsupervised", "graph_detectors": "rules on graph",
    "isolation_forest": "unsupervised", "cygnus_composite": "hybrid", "gbm_tabular": "supervised",
    "rf_graph": "supervised", "gbm_graph": "supervised",
}


# ----------------------------------------------------------------------------- rules baseline
def rules_baseline(transactions: List[Dict[str, Any]], features: pd.DataFrame) -> pd.DataFrame:
    """Conventional transaction-monitoring rules. Each looks at one account in isolation.

    R1 large transaction        a single transaction of BDT 25,000 or more (personal accounts)
    R2 daily volume             BDT 50,000 or more in or out in one day (personal accounts)
    R3 structuring              3+ transactions at 85-100% of the threshold in one day
    R4 velocity                 8+ transactions in one clock hour (personal accounts)
    R5 rapid pass-through       80%+ of receipts leave the same day and receipts total BDT 20,000+
    R6 many counterparties      10+ distinct senders or receivers within 2 hours (personal accounts)

    Agents and merchants are exempt from R1, R2, R4 and R6, as a real rules engine would
    whitelist them; otherwise every agent would alert every day.
    """
    tx = transactions_to_frame(transactions)
    day = np.floor((tx["t"] - tx["t"].min()) / 86400.0).astype(int)
    personal = features["tier_personal"] > 0

    daily_out = tx.groupby([tx["sender"], day])["amount"].sum().groupby(level=0).max()
    daily_in = tx.groupby([tx["receiver"], day])["amount"].sum().groupby(level=0).max()
    max_daily = pd.concat([daily_out, daily_in], axis=1).max(axis=1).reindex(features.index).fillna(0.0)

    near = tx[(tx["amount"] >= 0.85 * THRESHOLD) & (tx["amount"] < THRESHOLD)]
    near_day = day.loc[near.index]
    near_out = near.groupby([near["sender"], near_day]).size().groupby(level=0).max()
    near_in = near.groupby([near["receiver"], near_day]).size().groupby(level=0).max()
    max_near = pd.concat([near_out, near_in], axis=1).max(axis=1).reindex(features.index).fillna(0.0)

    fired = pd.DataFrame({
        "R1_large_transaction": personal & (features["maximum_transaction_amount"] >= 25000),
        "R2_daily_volume": personal & (max_daily >= 50000),
        "R3_structuring": max_near >= 3,
        "R4_velocity": personal & (features["max_tx_per_hour"] >= 8),
        "R5_rapid_passthrough": (features["same_day_turnover"] >= 0.8) & (features["total_incoming"] >= 20000),
        "R6_many_counterparties": personal & ((features["max_senders_2h"] >= 10) | (features["max_receivers_2h"] >= 10)),
    }, index=features.index)
    fired["rules_fired"] = fired.sum(axis=1)
    # Rules give no ranking beyond "how many fired"; break ties by volume so PR-AUC is defined
    volume = np.log1p(features["total_incoming"] + features["total_outgoing"])
    fired["score"] = fired["rules_fired"] + 0.5 * volume / max(volume.max(), 1.0)
    fired["alert"] = fired["rules_fired"] >= 1
    return fired


# ---------------------------------------------------------------------------------- metrics
def binary_metrics(y: np.ndarray, score: np.ndarray, alert: np.ndarray) -> Dict[str, float]:
    alert = alert.astype(bool)
    tp = int((alert & (y == 1)).sum())
    fp = int((alert & (y == 0)).sum())
    fn = int((~alert & (y == 1)).sum())
    tn = int((~alert & (y == 0)).sum())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / max(precision + recall, 1e-12),
        "false_positive_rate": fp / max(fp + tn, 1),
        "pr_auc": float(average_precision_score(y, score)),
        "roc_auc": float(roc_auc_score(y, score)),
        "alerts": tp + fp,
        "alerts_per_1000_accounts": 1000.0 * (tp + fp) / len(y),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
    }


def mean_std(rows: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    keys = rows[0].keys()
    return {k: {"mean": float(np.mean([r[k] for r in rows])), "std": float(np.std([r[k] for r in rows]))} for k in keys}


def prepare(seed: int, size: Dict[str, Any], exclude: Optional[Sequence[str]] = None, product: bool = True) -> Dict[str, Any]:
    """One labelled network with features, meta data and (optionally) the product pipeline's scores."""
    dataset = generate_mfs_dataset(seed=seed, exclude_typologies=list(exclude or []), **size)
    tiers = {acc: info["tier"] for acc, info in dataset.accounts.items()}
    features = build_account_features(dataset.transactions, tiers)
    meta = pd.DataFrame.from_dict(dataset.accounts, orient="index").reindex(features.index)
    bundle = {
        "seed": seed,
        "summary": dataset.summary(),
        "X": features,
        "y": meta["label"].values.astype(int),
        "typology": meta["typology"].fillna("none").values,
        "evasive": meta["evasive"].values.astype(bool),
        "tier": meta["tier"].values,
        "district": meta["district"].values,
        "rules": rules_baseline(dataset.transactions, features),
    }
    context = run_context_detectors(dataset.transactions, tiers)
    bundle["context"] = {name: np.isin(features.index.values, res["flagged_accounts"]) for name, res in context.items()}
    bundle["role"] = meta["role"].fillna("").values
    for flag in ("takeover_victim", "formal_remittance_agent", "risk_area_visitor"):
        bundle[flag] = meta[flag].values.astype(bool)
    if product:
        # Phase 1 = static-graph search + IsolationForest; current = flow tracing + trained classifier
        for key, temporal, supervised in (("phase1", False, False), ("current", None, True)):
            result = run_pipeline(
                dataset.transactions, contamination=0.05, temporal=temporal,
                use_supervised=supervised, account_tiers=tiers,
            )
            frame = pd.DataFrame(
                {a["account_id"]: {
                    "risk_score": a["risk_score"],
                    "graph_component": a["scoring_breakdown"]["graph_component"],
                } for a in result["accounts"]}
            ).T.reindex(features.index).fillna(0.0)
            bundle[key] = frame
    return bundle


# -------------------------------------------------------------------------------- evaluation
def evaluate(quick: bool = False) -> Dict[str, Any]:
    started = time.time()
    size = QUICK_SIZE if quick else EVAL_SIZE
    test_seeds = TEST_SEEDS[:2] if quick else TEST_SEEDS
    log = lambda msg: print(f"[{time.time() - started:6.0f}s] {msg}", flush=True)  # noqa: E731

    log("building training and validation networks")
    train = [prepare(s, size, product=False) for s in TRAIN_SEEDS]
    val = prepare(VALIDATION_SEED, size, product=False)
    X_train = pd.concat([b["X"] for b in train])
    y_train = np.concatenate([b["y"] for b in train])

    log("training supervised models")
    feature_sets = {
        "gbm_tabular": TABULAR_FEATURES,
        "rf_graph": ALL_FEATURES,
        "gbm_graph": ALL_FEATURES,
        "gbm_graph_no_account_type": [f for f in ALL_FEATURES if f not in FEATURE_FAMILIES["account_type"]],
    }
    makers = {"gbm_tabular": make_gbm, "rf_graph": make_random_forest, "gbm_graph": make_gbm, "gbm_graph_no_account_type": make_gbm}
    models, thresholds = {}, {}
    for name, columns in feature_sets.items():
        models[name] = makers[name]().fit(X_train[columns].values, y_train)
        thresholds[name] = best_f1_threshold(val["y"], models[name].predict_proba(val["X"][columns].values)[:, 1])

    log("building test networks and running the product pipeline on them")
    tests = [prepare(s, size, product=True) for s in test_seeds]

    def model_outputs(bundle: Dict[str, Any]) -> Dict[str, Dict[str, np.ndarray]]:
        X = bundle["X"]
        out: Dict[str, Dict[str, np.ndarray]] = {
            "rules_baseline": {"score": bundle["rules"]["score"].values, "alert": bundle["rules"]["alert"].values},
            "phase1_composite": {"score": bundle["phase1"]["risk_score"].values, "alert": bundle["phase1"]["risk_score"].values >= 40},
            "graph_detectors": {"score": bundle["current"]["graph_component"].values, "alert": bundle["current"]["graph_component"].values >= 30},
            "cygnus_composite": {"score": bundle["current"]["risk_score"].values, "alert": bundle["current"]["risk_score"].values >= 40},
        }
        detector = AnomalyDetector(contamination=0.03, random_state=42).fit(X[ALL_FEATURES])
        iso = detector.compute_anomaly_scores(X[ALL_FEATURES])
        out["isolation_forest"] = {"score": iso["ml_anomaly_score"].values, "alert": iso["is_anomaly"].values}
        for name, columns in feature_sets.items():
            proba = models[name].predict_proba(X[columns].values)[:, 1]
            out[name] = {"score": proba, "alert": proba >= thresholds[name]}
        return out

    outputs = [model_outputs(b) for b in tests]
    model_names = list(MODEL_LABELS)

    log("scoring models")
    comparison = {}
    for name in model_names:
        per_seed = [binary_metrics(b["y"], o[name]["score"], o[name]["alert"]) for b, o in zip(tests, outputs)]
        comparison[name] = {"label": MODEL_LABELS[name], "kind": MODEL_KIND[name], **mean_std(per_seed)}

    # Recall per typology (and for the evasive variants), pooled over the test networks
    y_all = np.concatenate([b["y"] for b in tests])
    typ_all = np.concatenate([b["typology"] for b in tests])
    evasive_all = np.concatenate([b["evasive"] for b in tests])
    tier_all = np.concatenate([b["tier"] for b in tests])
    district_all = np.concatenate([b["district"] for b in tests])
    alerts_all = {n: np.concatenate([o[n]["alert"] for o in outputs]).astype(bool) for n in list(MODEL_LABELS) + ["gbm_graph_no_account_type"]}
    scores_all = {n: np.concatenate([o[n]["score"] for o in outputs]) for n in list(MODEL_LABELS) + ["gbm_graph_no_account_type"]}

    typology_recall = {}
    for typology in TYPOLOGIES:
        mask = (typ_all == typology) & (y_all == 1)
        typology_recall[typology] = {
            "label": TYPOLOGY_LABELS[typology],
            "accounts": int(mask.sum()),
            "recall": {n: float(alerts_all[n][mask].mean()) for n in model_names},
        }
    evasive_mask = evasive_all & (y_all == 1)
    plain_mask = ~evasive_all & (y_all == 1)
    evasive_recall = {
        "evasive_accounts": int(evasive_mask.sum()),
        "plain_accounts": int(plain_mask.sum()),
        "evasive": {n: float(alerts_all[n][evasive_mask].mean()) for n in model_names},
        "plain": {n: float(alerts_all[n][plain_mask].mean()) for n in model_names},
    }

    # What graph intelligence adds over rules: suspicious accounts no rule fired on
    missed_by_rules = (y_all == 1) & ~alerts_all["rules_baseline"]
    graph_vs_rules = {
        "suspicious_accounts": int((y_all == 1).sum()),
        "missed_by_rules": int(missed_by_rules.sum()),
        "of_those_caught_by_graph_detectors": int((missed_by_rules & alerts_all["graph_detectors"]).sum()),
        "of_those_caught_by_gbm_graph": int((missed_by_rules & alerts_all["gbm_graph"]).sum()),
        "missed_by_rules_by_typology": {
            t: {
                "missed_by_rules": int((missed_by_rules & (typ_all == t)).sum()),
                "caught_by_gbm_graph": int((missed_by_rules & (typ_all == t) & alerts_all["gbm_graph"]).sum()),
                "caught_by_graph_detectors": int((missed_by_rules & (typ_all == t) & alerts_all["graph_detectors"]).sum()),
            } for t in TYPOLOGIES
        },
        "rule_false_positives": int(((y_all == 0) & alerts_all["rules_baseline"]).sum()),
        "gbm_graph_false_positives": int(((y_all == 0) & alerts_all["gbm_graph"]).sum()),
    }

    log("feature-family ablation")
    ladder = [
        ("transactional", ["transactional", "account_type"]),
        ("+ temporal", ["transactional", "account_type", "temporal"]),
        ("+ graph and flow tracing", ["transactional", "account_type", "temporal", "graph"]),
        ("+ 2-hop neighbourhood", ["transactional", "account_type", "temporal", "graph", "neighbourhood"]),
    ]
    ablation = []
    for label, families in ladder:
        columns = [c for fam in families for c in FEATURE_FAMILIES[fam]]
        model = make_gbm().fit(X_train[columns].values, y_train)
        pr = [float(average_precision_score(b["y"], model.predict_proba(b["X"][columns].values)[:, 1])) for b in tests]
        ablation.append({"features": label, "n_features": len(columns), "pr_auc_mean": float(np.mean(pr)), "pr_auc_std": float(np.std(pr))})

    log("permutation feature importance")
    first = tests[0]
    importance = permutation_importance(
        models["gbm_graph"], first["X"][ALL_FEATURES].values, first["y"],
        scoring="average_precision", n_repeats=3 if quick else 5, random_state=42, n_jobs=-1,
    )
    ranked = sorted(zip(ALL_FEATURES, importance.importances_mean, importance.importances_std), key=lambda r: -r[1])
    family_importance: Dict[str, float] = {}
    for name, mean, _ in ranked:
        family_importance[feature_family(name)] = family_importance.get(feature_family(name), 0.0) + max(float(mean), 0.0)
    total_importance = sum(family_importance.values()) or 1.0
    feature_importance = {
        "method": "Permutation importance on a held-out network: drop in PR-AUC when one feature is shuffled.",
        "top_features": [
            {"feature": name, "family": feature_family(name), "importance": float(mean), "std": float(std)}
            for name, mean, std in ranked[:15]
        ],
        "by_family_share": {fam: value / total_importance for fam, value in sorted(family_importance.items(), key=lambda kv: -kv[1])},
    }

    log("leave-one-typology-out (unseen typology)")
    unseen = {}
    for typology in TYPOLOGIES:
        held = [prepare(s, size, exclude=[typology], product=False) for s in TRAIN_SEEDS]
        held_val = prepare(VALIDATION_SEED, size, exclude=[typology], product=False)
        model = make_gbm().fit(pd.concat([b["X"] for b in held])[ALL_FEATURES].values, np.concatenate([b["y"] for b in held]))
        threshold = best_f1_threshold(held_val["y"], model.predict_proba(held_val["X"][ALL_FEATURES].values)[:, 1])
        proba = np.concatenate([model.predict_proba(b["X"][ALL_FEATURES].values)[:, 1] for b in tests])
        target = (typ_all == typology) & (y_all == 1)
        subset = target | (y_all == 0)  # this typology against all normal accounts
        unseen[typology] = {
            "label": TYPOLOGY_LABELS[typology],
            "accounts": int(target.sum()),
            "recall_when_never_trained_on_it": float((proba >= threshold)[target].mean()),
            "recall_when_trained_on_it": float(alerts_all["gbm_graph"][target].mean()),
            "recall_isolation_forest": float(alerts_all["isolation_forest"][target].mean()),
            "recall_graph_detectors": float(alerts_all["graph_detectors"][target].mean()),
            "recall_rules": float(alerts_all["rules_baseline"][target].mean()),
            "pr_auc_when_never_trained_on_it": float(average_precision_score(y_all[subset], proba[subset])),
            "pr_auc_when_trained_on_it": float(average_precision_score(y_all[subset], scores_all["gbm_graph"][subset])),
        }

    log("bias check")
    bias_models = ["rules_baseline", "phase1_composite", "cygnus_composite", "gbm_graph_no_account_type", "gbm_graph"]
    by_tier: Dict[str, Any] = {}
    for tier in ("personal", "agent", "merchant"):
        legit = (tier_all == tier) & (y_all == 0)
        bad = (tier_all == tier) & (y_all == 1)
        by_tier[tier] = {
            "legitimate_accounts": int(legit.sum()),
            "suspicious_accounts": int(bad.sum()),
            "false_positive_rate": {n: float(alerts_all[n][legit].mean()) for n in bias_models},
            "recall": {n: (float(alerts_all[n][bad].mean()) if bad.sum() else None) for n in bias_models},
        }
    fpr_gap = {}
    for n in bias_models:
        rates = [by_tier[t]["false_positive_rate"][n] for t in by_tier]
        fpr_gap[n] = {"max": max(rates), "min": min(rates), "gap_percentage_points": 100 * (max(rates) - min(rates))}

    legit_personal = (tier_all == "personal") & (y_all == 0)
    by_district = {}
    for n in ("rules_baseline", "gbm_graph"):
        table = pd.crosstab(district_all[legit_personal], alerts_all[n][legit_personal])
        rates = (table[True] / table.sum(axis=1)) if True in table.columns else pd.Series(0.0, index=table.index)
        p_value = float(chi2_contingency(table.values)[1]) if table.shape[1] == 2 and (table.values.sum(axis=0) > 0).all() else None
        by_district[n] = {
            "districts": int(len(rates)),
            "min_false_positive_rate": float(rates.min()),
            "max_false_positive_rate": float(rates.max()),
            "chi_square_p_value": p_value,
            "independent_of_district": (p_value is None) or (p_value > 0.05),
        }
    bias = {
        "by_account_tier": by_tier,
        "false_positive_rate_gap_between_tiers": fpr_gap,
        "by_district_legitimate_personal_accounts": by_district,
        "note": (
            "The Phase 1 score flagged almost every legitimate agent, because collecting from many customers and "
            "turning money around quickly is what an agent does. The current score is tier-aware: fan-in, fan-out "
            "and rapid movement are not counted against agents and merchants, and their statistical outlier score "
            "is replaced by the trained classifier. District is never a model input. Account type (personal / agent / merchant) is a model input in "
            "gbm_graph and left out of gbm_graph_no_account_type, so the effect of giving the model the "
            "account type can be read from the two columns."
        ),
    }

    log("context detectors (risk-area takeover, hundi)")
    role_all = np.concatenate([b["role"] for b in tests])

    def pooled(key: str) -> np.ndarray:
        return np.concatenate([b[key] for b in tests])

    def detector_metrics(name: str, truth: np.ndarray) -> Dict[str, Any]:
        flagged = np.concatenate([b["context"][name] for b in tests])
        tp = int((flagged & truth).sum())
        fp = int((flagged & ~truth).sum())
        return {
            "true_cases": int(truth.sum()),
            "flagged": int(flagged.sum()),
            "true_positives": tp,
            "false_positives": fp,
            "precision": tp / max(tp + fp, 1),
            "recall": tp / max(int(truth.sum()), 1),
            "false_positive_rate": fp / max(int((~truth).sum()), 1),
        }

    takeover_flags = np.concatenate([b["context"]["location_anomaly"] for b in tests])
    hundi_flags = np.concatenate([b["context"]["hundi_operator"] for b in tests])
    residents = np.isin(district_all, [12, 13]) & (tier_all == "personal")
    context_detectors = {
        "location_anomaly": {
            "label": "Risk-area account takeover (customer at risk)",
            **detector_metrics("location_anomaly", pooled("takeover_victim")),
            "legitimate_lookalikes": {
                "risk_area_residents": int(residents.sum()),
                "risk_area_residents_flagged": int((takeover_flags & residents & ~pooled("takeover_victim")).sum()),
                "risk_area_visitors": int(pooled("risk_area_visitor").sum()),
                "risk_area_visitors_flagged": int((takeover_flags & pooled("risk_area_visitor") & ~pooled("takeover_victim")).sum()),
            },
        },
        "takeover_collector": {"label": "Takeover collector", **detector_metrics("takeover_collector", role_all == "takeover_collector")},
        "hundi_operator": {
            "label": "Hundi operator",
            **detector_metrics("hundi_operator", role_all == "operator"),
            "legitimate_lookalikes": {
                "licensed_remittance_agents": int(pooled("formal_remittance_agent").sum()),
                "licensed_remittance_agents_flagged": int((hundi_flags & pooled("formal_remittance_agent")).sum()),
            },
        },
        "hundi_funder": {"label": "Hundi funder", **detector_metrics("hundi_funder", role_all == "feeder")},
        "note": (
            "Both detectors compare an account with its own history. A takeover alert needs at least two signals "
            "(area new for this customer, new handset, unusually fast outflow, new receivers); a hundi alert needs "
            "informal funding, a payout to five or more beneficiaries and the same beneficiaries paid in two or more cycles. "
            "The simulated hundi and takeover cases are clean, so these figures are an upper bound."
        ),
    }

    # Analyst workload: alerts needed to reach the rules' recall, and recall at the rules' alert budget
    order = np.argsort(-scores_all["gbm_graph"])
    hits = np.cumsum(y_all[order] == 1)
    rules_alerts = int(alerts_all["rules_baseline"].sum())
    rules_tp = int((alerts_all["rules_baseline"] & (y_all == 1)).sum())
    needed = int(np.searchsorted(hits, rules_tp) + 1) if rules_tp > 0 else 0
    total_pos = int((y_all == 1).sum())
    gbm_alerts = int(alerts_all["gbm_graph"].sum())
    gbm_tp = int((alerts_all["gbm_graph"] & (y_all == 1)).sum())
    n_accounts = len(y_all)
    workload = {
        "assumption_minutes_per_alert": ANALYST_MINUTES_PER_ALERT,
        "accounts_scored": n_accounts,
        "rules": {"alerts": rules_alerts, "true_positives": rules_tp, "recall": rules_tp / total_pos,
                  "analyst_hours": rules_alerts * ANALYST_MINUTES_PER_ALERT / 60.0},
        "gbm_graph_at_operating_point": {"alerts": gbm_alerts, "true_positives": gbm_tp, "recall": gbm_tp / total_pos,
                                          "analyst_hours": gbm_alerts * ANALYST_MINUTES_PER_ALERT / 60.0},
        "alerts_gbm_needs_to_match_rules_recall": needed,
        "alert_reduction_at_equal_recall": 1.0 - needed / max(rules_alerts, 1),
        "recall_gbm_at_rules_alert_budget": float(hits[min(rules_alerts, n_accounts) - 1] / total_pos) if rules_alerts else 0.0,
        "alert_reduction_at_operating_point": 1.0 - gbm_alerts / max(rules_alerts, 1),
        "analyst_hours_saved_at_operating_point": (rules_alerts - gbm_alerts) * ANALYST_MINUTES_PER_ALERT / 60.0,
        "minutes_of_review_per_true_positive": {
            "rules": rules_alerts * ANALYST_MINUTES_PER_ALERT / max(rules_tp, 1),
            "gbm_graph": gbm_alerts * ANALYST_MINUTES_PER_ALERT / max(gbm_tp, 1),
        },
    }

    log("done")
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quick_mode": quick,
        "dataset": {
            "description": (
                "Synthetic Bangladesh-style MFS networks (personal wallets, agents, merchants) with six planted "
                "typologies and legitimate look-alike traffic. Models are trained on two networks, tuned on a "
                "third and tested on separate networks generated with different random seeds."
            ),
            "train_seeds": list(TRAIN_SEEDS),
            "validation_seed": VALIDATION_SEED,
            "test_seeds": list(test_seeds),
            "train_networks": [b["summary"] for b in train],
            "test_networks": [b["summary"] for b in tests],
            "test_transactions_total": int(sum(b["summary"]["transactions"] for b in tests)),
            "test_accounts_total": int(n_accounts),
            "test_suspicious_total": total_pos,
            "all_networks_transactions_total": int(sum(b["summary"]["transactions"] for b in train + [val] + tests)),
            "threshold_bdt": THRESHOLD,
            "typologies": TYPOLOGY_LABELS,
            "n_features": len(ALL_FEATURES),
            "features_by_family": {fam: len(cols) for fam, cols in FEATURE_FAMILIES.items()},
        },
        "operating_points": {
            "rules_baseline": "alert when any rule fires",
            "phase1_composite": "risk score >= 40 (MEDIUM and above)",
            "graph_detectors": "graph component >= 30",
            "isolation_forest": "flagged anomaly at 3% contamination",
            "cygnus_composite": "risk score >= 40 (MEDIUM and above)",
            "supervised": {n: thresholds[n] for n in ("gbm_tabular", "rf_graph", "gbm_graph")},
            "supervised_note": "threshold with the best F1 on the validation network, then frozen",
        },
        "model_comparison": comparison,
        "recall_by_typology": typology_recall,
        "recall_evasive_vs_plain": evasive_recall,
        "graph_vs_rules": graph_vs_rules,
        "feature_ablation": ablation,
        "feature_importance": feature_importance,
        "unseen_typology": unseen,
        "context_detectors": context_detectors,
        "bias": bias,
        "workload": workload,
        "limitations": [
            "All data is synthetic. The simulator and the detectors were built by the same team, so these numbers are an upper bound on what to expect from real upay traffic.",
            "Suspicious accounts are about 2.5% of the test networks, far more common than in production; precision on real data would be lower at the same threshold.",
            "Labels are exact by construction. Real labels (filed STRs, confirmed fraud) are delayed, incomplete and noisy.",
            "The neighbourhood features are fixed 2-hop averages, not a trained graph neural network; a learned GNN is the next step once real labelled data is available.",
            "The analyst-workload figures assume 20 minutes of review per alert. That is an assumption, not a measurement from a pilot.",
        ],
        "runtime_seconds": round(time.time() - started, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 model evaluation")
    parser.add_argument("--quick", action="store_true", help="Small networks (for tests); does not overwrite the published results")
    parser.add_argument("--out", type=str, help="Write the results JSON here instead of the default locations")
    args = parser.parse_args()
    results = evaluate(quick=args.quick)
    if args.out or args.quick:
        target = args.out or os.path.join(PROJECT_ROOT, "docs", "evaluation", "phase2_results_quick.json")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"wrote {target}")
        return
    from ml.report_writer import publish  # local import: only needed for the full run

    publish(model_results=results)


if __name__ == "__main__":
    main()
