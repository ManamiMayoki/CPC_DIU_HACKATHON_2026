"""Supervised suspicious-account classifier trained on the labelled synthetic MFS network.

The reference model is a gradient-boosted tree ensemble over the full feature store
(transactional + temporal + graph + 2-hop neighbourhood features + account type). It is trained
on simulated data only, so its probabilities are a ranking signal for analysts, not evidence.

`load_or_train()` caches the fitted model next to this file so the API can score without
retraining; `python -m ml.supervised` (run at image build) creates the cache.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.synthetic.mfs_generator import generate_mfs_dataset  # noqa: E402
from ml.feature_store import FEATURE_FAMILIES, build_account_features, family_columns  # noqa: E402

ARTIFACT_DIR = os.path.join(CURRENT_DIR, "artifacts")
ARTIFACT_PATH = os.path.join(ARTIFACT_DIR, "gbm_graph.joblib")

# Dataset size used for training and evaluation (about 137,000 transactions per network)
EVAL_SIZE = {"n_personal": 12000, "n_agents": 480, "n_merchants": 640, "fraud_scale": 0.5}
TRAIN_SEEDS = (7, 8)
VALIDATION_SEED = 9

ALL_FEATURES: List[str] = family_columns(["transactional", "temporal", "graph", "neighbourhood", "account_type"])
# What a conventional per-account monitoring system can compute: no graph, no flow tracing
TABULAR_FEATURES: List[str] = (
    FEATURE_FAMILIES["transactional"]
    + [f for f in FEATURE_FAMILIES["temporal"] if not f.startswith("dwell_")]
    + FEATURE_FAMILIES["account_type"]
)


def make_gbm(random_state: int = 42) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0,
        early_stopping=False, random_state=random_state,
    )


def make_random_forest(random_state: int = 42) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample", n_jobs=-1, random_state=random_state,
    )


def labelled_features(seed: int, size: Optional[Dict[str, Any]] = None, exclude: Optional[Sequence[str]] = None):
    """Generates one labelled network and returns (dataset, feature frame, labels aligned to the frame)."""
    dataset = generate_mfs_dataset(seed=seed, exclude_typologies=list(exclude or []), **(size or EVAL_SIZE))
    tiers = {acc: info["tier"] for acc, info in dataset.accounts.items()}
    features = build_account_features(dataset.transactions, tiers)
    labels = np.array([dataset.accounts[acc]["label"] for acc in features.index])
    return dataset, features, labels


def training_matrix(seeds: Sequence[int] = TRAIN_SEEDS, size: Optional[Dict[str, Any]] = None,
                    exclude: Optional[Sequence[str]] = None):
    frames, labels = [], []
    for seed in seeds:
        _, features, y = labelled_features(seed, size, exclude)
        frames.append(features)
        labels.append(y)
    return pd.concat(frames), np.concatenate(labels)


def best_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Decision threshold with the best F1 on a validation set."""
    from sklearn.metrics import precision_recall_curve

    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    return float(thresholds[int(np.argmax(f1))])


def train_reference_model(size: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    features, labels = training_matrix(size=size)
    model = make_gbm().fit(features[ALL_FEATURES].values, labels)
    _, val_features, val_labels = labelled_features(VALIDATION_SEED, size)
    val_scores = model.predict_proba(val_features[ALL_FEATURES].values)[:, 1]
    return {
        "model": model,
        "features": ALL_FEATURES,
        "threshold": best_f1_threshold(val_labels, val_scores),
        "trained_on": {"seeds": list(TRAIN_SEEDS), "accounts": int(len(labels)), "suspicious": int(labels.sum())},
    }


_cached: Optional[Dict[str, Any]] = None


def load_or_train(force: bool = False) -> Dict[str, Any]:
    global _cached
    if _cached is not None and not force:
        return _cached
    import joblib

    if not force and os.path.exists(ARTIFACT_PATH):
        try:
            _cached = joblib.load(ARTIFACT_PATH)
            return _cached
        except Exception:
            pass  # stale or incompatible cache: retrain below
    bundle = train_reference_model()
    try:
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        joblib.dump(bundle, ARTIFACT_PATH)
    except OSError:
        pass  # read-only filesystem: keep the model in memory only
    _cached = bundle
    return bundle


def score_accounts(features: pd.DataFrame, bundle: Optional[Dict[str, Any]] = None) -> pd.Series:
    """Probability-like suspicion score per account from the reference model."""
    bundle = bundle or load_or_train()
    matrix = features.reindex(columns=bundle["features"], fill_value=0.0).values
    return pd.Series(bundle["model"].predict_proba(matrix)[:, 1], index=features.index)


# Plain-language names for the features that most often drive a score
FEATURE_LABELS = {
    "forward_share_fast": "share of received money forwarded within an hour",
    "forward_share_slow": "share of received money forwarded within 12 hours",
    "forward_count_fast": "payments forwarded within an hour of receipt",
    "forward_count_slow": "payments forwarded within 12 hours of receipt",
    "chain_length_fast": "length of the fast flow chain it sits in (hops)",
    "chain_length_slow": "length of the flow chain it sits in (hops)",
    "cycle_count_fast": "times money looped back within the hour",
    "cycle_count_slow": "times money looped back to it",
    "dwell_fast_s": "seconds money rests before being forwarded",
    "dwell_slow_s": "seconds money rests before being forwarded (12h window)",
    "passthrough_ratio": "pass-through ratio (money out vs money in)",
    "same_day_turnover": "share of receipts that leave the same day",
    "near_threshold_out": "payments sent just under the threshold",
    "near_threshold_in": "payments received just under the threshold",
    "sub_threshold_share": "share of transactions at 50-100% of the threshold",
    "max_senders_2h": "most distinct senders within 2 hours",
    "max_receivers_2h": "most distinct receivers within 2 hours",
    "in_degree": "number of distinct senders",
    "out_degree": "number of distinct receivers",
    "reciprocity": "share of counterparties it both pays and is paid by",
    "night_share": "share of activity between midnight and 6am",
    "total_incoming": "total received (BDT)",
    "total_outgoing": "total sent (BDT)",
    "average_transaction_amount": "average transaction amount (BDT)",
    "maximum_transaction_amount": "largest transaction (BDT)",
    "counterparty_diversity": "distinct counterparties per transaction",
    "triad_cycles": "three-account loops through it",
    "transaction_count": "number of transactions",
    "active_days": "days active",
}


def feature_label(name: str) -> str:
    if name in FEATURE_LABELS:
        return FEATURE_LABELS[name]
    for prefix, text in (("nb_in_", "average over the accounts that pay it: "),
                         ("nb_out_", "average over the accounts it pays: "),
                         ("nb2_", "average over its 2-hop neighbourhood: ")):
        if name.startswith(prefix):
            return text + name[len(prefix):].replace("_", " ")
    return name.replace("_", " ")


def explain_accounts(
    features: pd.DataFrame,
    account_ids: Sequence[str],
    bundle: Optional[Dict[str, Any]] = None,
    top_k: int = 3,
    candidates: int = 14,
) -> Dict[str, List[Dict[str, Any]]]:
    """Per-account drivers of the model score, by occlusion.

    For each account, each candidate feature is replaced with the population median and the
    drop in the model's probability is recorded. The features whose removal lowers the score
    most are that account's drivers. Model-agnostic and exact for this model, no SHAP needed.
    """
    bundle = bundle or load_or_train()
    columns = bundle["features"]
    matrix = features.reindex(columns=columns, fill_value=0.0)
    medians = matrix.median(axis=0).values
    wanted = [a for a in account_ids if a in matrix.index]
    if not wanted:
        return {}
    rows = matrix.loc[wanted].values
    base = bundle["model"].predict_proba(rows)[:, 1]
    # Candidates: the features where the selected accounts differ most from the population
    spread = matrix.std(axis=0).values + 1e-9
    deviation = np.abs(rows - medians) / spread
    explanations: Dict[str, List[Dict[str, Any]]] = {}
    for i, account in enumerate(wanted):
        picks = [j for j in np.argsort(-deviation[i]) if not columns[j].startswith("tier_")][:candidates]
        occluded = np.repeat(rows[i:i + 1], len(picks), axis=0)
        for k, j in enumerate(picks):
            occluded[k, j] = medians[j]
        drops = base[i] - bundle["model"].predict_proba(occluded)[:, 1]
        order = [k for k in np.argsort(-drops)[:top_k] if drops[k] > 0.005]
        if not order:
            # No single feature moves the score on its own (several agree); list the most unusual ones
            order = list(range(min(top_k, len(picks))))
        explanations[account] = [
            {
                "feature": columns[picks[k]],
                "label": feature_label(columns[picks[k]]),
                "value": round(float(rows[i, picks[k]]), 3),
                "typical": round(float(medians[picks[k]]), 3),
                "contribution": round(max(float(drops[k]), 0.0), 4),
            }
            for k in order
        ]
    return explanations


if __name__ == "__main__":
    trained = load_or_train(force=True)
    print(f"Reference model trained on {trained['trained_on']} -> {ARTIFACT_PATH} (threshold {trained['threshold']:.3f})")
