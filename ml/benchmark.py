"""Throughput and latency benchmark.

Measures, at growing network sizes:
  scoring path   feature store (incl. time-ordered flow tracing) + trained-model scoring
  full pipeline  validation + NetworkX graph + 7 detectors + scoring + evidence text
and, when --api is given, request latency of the running backend.

Run:  python -m ml.benchmark [--api http://localhost:5001] [--quick]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import resource
import sys
import time
import urllib.request
from typing import Any, Dict, List, Optional

import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
for p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "graph-engine")):
    if p not in sys.path:
        sys.path.insert(0, p)

from data.synthetic.mfs_generator import generate_mfs_dataset  # noqa: E402
from ml.feature_store import build_account_features  # noqa: E402
from ml.inference import run_pipeline  # noqa: E402
from ml.supervised import load_or_train, score_accounts  # noqa: E402

SCORING_SIZES = [1000, 4000, 12000, 40000, 90000]  # personal wallets; about 11.5 transactions each
FULL_PIPELINE_SIZES = [1000, 4000, 12000]


def _network(n_personal: int):
    dataset = generate_mfs_dataset(
        seed=555, n_personal=n_personal, n_agents=max(20, n_personal // 25),
        n_merchants=max(30, n_personal // 19), fraud_scale=0.5,
    )
    return dataset, {acc: info["tier"] for acc, info in dataset.accounts.items()}


def _peak_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def scoring_path(sizes: List[int]) -> List[Dict[str, Any]]:
    bundle = load_or_train()
    rows = []
    for n in sizes:
        dataset, tiers = _network(n)
        start = time.perf_counter()
        features = build_account_features(dataset.transactions, tiers)
        mid = time.perf_counter()
        score_accounts(features, bundle)
        end = time.perf_counter()
        rows.append({
            "transactions": len(dataset.transactions),
            "accounts": len(features),
            "feature_seconds": mid - start,
            "scoring_seconds": end - mid,
            "total_seconds": end - start,
            "transactions_per_second": len(dataset.transactions) / (end - start),
            "peak_memory_mb": _peak_mb(),
        })
        print(f"scoring path  {rows[-1]['transactions']:>9,} tx  {rows[-1]['total_seconds']:.2f}s", flush=True)
    return rows


def full_pipeline(sizes: List[int]) -> List[Dict[str, Any]]:
    rows = []
    for n in sizes:
        dataset, tiers = _network(n)
        start = time.perf_counter()
        result = run_pipeline(dataset.transactions, contamination=0.05, account_tiers=tiers)
        elapsed = time.perf_counter() - start
        rows.append({
            "transactions": len(dataset.transactions),
            "accounts": result["total_accounts_analyzed"],
            "total_seconds": elapsed,
            "transactions_per_second": len(dataset.transactions) / elapsed,
            "detection_mode": result["models"]["detection_mode"],
        })
        print(f"full pipeline {rows[-1]['transactions']:>9,} tx  {elapsed:.2f}s", flush=True)
    return rows


def micro_batch() -> Dict[str, Any]:
    """Re-score only the most recent 24 hours of a 14-day network."""
    dataset, tiers = _network(12000)
    last_day = dataset.transactions[-1]["timestamp"][:10]
    recent = [t for t in dataset.transactions if t["timestamp"][:10] == last_day]
    bundle = load_or_train()
    start = time.perf_counter()
    features = build_account_features(recent, tiers)
    score_accounts(features, bundle)
    elapsed = time.perf_counter() - start
    return {"transactions": len(recent), "accounts": len(features), "total_seconds": elapsed}


def api_latency(base_url: str, requests: int = 200) -> Optional[Dict[str, Any]]:
    def call(method: str, path: str, token: Optional[str] = None, body: Optional[dict] = None) -> bytes:
        req = urllib.request.Request(base_url + path, method=method, data=json.dumps(body).encode() if body else None)
        if body:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.read()

    try:
        token = json.loads(call("POST", "/api/auth/demo", body={"role": "analyst"}))["token"]
    except Exception as exc:
        print(f"API latency skipped: {exc}")
        return None
    endpoints = [
        "/api/health", "/api/stats", "/api/accounts?limit=50", "/api/accounts/ACC_MULE_HUB",
        "/api/network/ACC_MULE_HUB?hops=2", "/api/accounts/ACC_MULE_HUB/profile", "/api/cases", "/api/pipeline",
    ]
    rows = []
    for path in endpoints:
        call("GET", path, token)  # warm-up
        samples = []
        for _ in range(requests):
            start = time.perf_counter()
            call("GET", path, token)
            samples.append(1000 * (time.perf_counter() - start))
        rows.append({
            "endpoint": f"GET {path}",
            "p50_ms": float(np.percentile(samples, 50)),
            "p95_ms": float(np.percentile(samples, 95)),
            "p99_ms": float(np.percentile(samples, 99)),
        })
        print(f"api {path:45s} p50 {rows[-1]['p50_ms']:.1f} ms  p95 {rows[-1]['p95_ms']:.1f} ms", flush=True)
    return {"requests_per_endpoint": requests, "base_url": base_url, "endpoints": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Cygnus throughput and latency benchmark")
    parser.add_argument("--api", type=str, help="Base URL of a running backend, e.g. http://localhost:5001")
    parser.add_argument("--quick", action="store_true", help="Small sizes only; prints instead of publishing")
    args = parser.parse_args()

    sizes = SCORING_SIZES[:2] if args.quick else SCORING_SIZES
    full_sizes = FULL_PIPELINE_SIZES[:1] if args.quick else FULL_PIPELINE_SIZES
    cores = os.cpu_count()
    result = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "machine": f"a {cores}-core laptop ({platform.machine()}, Python {platform.python_version()}), single process, inside Docker",
        "scoring_path": scoring_path(sizes),
        "full_pipeline": full_pipeline(full_sizes),
        "micro_batch": micro_batch() if not args.quick else None,
        "api_latency": api_latency(args.api) if args.api else None,
        "note": (
            "Single process, in memory, no GPU. The scoring path is what a production deployment would run per "
            "micro-batch; the full pipeline also builds a NetworkX graph and writes evidence text for every account. "
            "A streaming bus (Kafka) and a graph database (Neo4j) are the planned next step and are not part of this measurement."
        ),
    }
    if args.quick:
        print(json.dumps(result, indent=2))
        return
    from ml.report_writer import publish

    publish(benchmark=result)


if __name__ == "__main__":
    main()
