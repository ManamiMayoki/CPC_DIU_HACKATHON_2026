# Cygnus AI - Celestial Intelligence for Financial Security & AML Compliance

---

## 1. Executive Summary

This repository hosts the core intelligence layer of **Cygnus AI**—an end-to-end framework combining graph topology algorithms and unsupervised machine learning to detect suspicious financial transaction patterns on synthetic datasets.

```
Synthetic Transactions
        ↓
Transaction Validation (Security)
        ↓
NetworkX Transaction Graph
        ↓
Network Pattern Detection (Fan-In, Fan-Out, Time-Ordered Cycles, Chains, Rapid Movement, Structuring, Coordinated Networks)
        ↓
Graph Topological Features + ML Behavioral Features
        ↓
Isolation Forest Anomaly Detection
        ↓
Explainable Composite Risk Scoring (0–100)
        ↓
Grounded Evidence Generation + AI Investigator Case Briefing
        ↓
Structured Integration Contract for Member 1
```

---

## 2. Implemented Architecture & Modules

### Member 2: Graph Algorithms & Network Detection
- **`graph-engine/graph.py`**: Builds NetworkX directed graphs (`nx.DiGraph` & `nx.MultiDiGraph`) with account nodes and transaction edges preserving amounts, timestamps, and IDs.
- **`graph-engine/patterns.py`**: Algorithmic detectors for 7 suspicious patterns:
  1. **Fan-In**: Many distinct senders into one collector, with a burst window (most senders within 2 hours).
  2. **Fan-Out**: One distributor to many distinct receivers, with the same burst window.
  3. **Circular Flows**: Directed cycles ($A \to B \to C \to A$) that must happen **in time order** within 6 hours and return at least 50% of the value, so random peer-to-peer loops are not flagged.
  4. **Transaction Chains**: Multi-hop linear paths ($\ge 3$ hops).
  5. **Rapid Fund Movement**: An inflow of at least 1,000 followed by a comparable outflow (70% to 110%) within the hour.
  6. **Structuring (smurfing)**: 3 or more transfers just under the reporting threshold (85% to 100% of 10,000) within 24 hours, flagging both the splitter and the collector.
  7. **Coordinated Networks**: Dense interconnected clusters of 4 or more accounts.
- **`graph-engine/features.py`**: Account-level graph feature extraction (`in_degree`, `out_degree`, `weighted_degrees`, `counterparties`, `cycle_count`, `chain_length`, `structuring_detected`, `near_threshold_tx_count`, `network_size`, `suspicious_neighbor_count`).
- **`graph-engine/engine.py`**: Graph analysis orchestrator.

### Member 3: ML Anomaly Detection, Risk Scoring & Security
- **`ml/validation.py`**: Rigorous data validation preventing negative/zero amounts, `NaN`, `Inf`, extreme values ($> 10^9$), invalid timestamps, self-transfers, duplicate transaction IDs, and malformed inputs.
- **`ml/features.py`**: Behavioral feature extraction (transaction counts, inflows/outflows, velocity, ratios) and merged ML feature vector creation.
- **`ml/model.py`**: Unsupervised anomaly detector using `IsolationForest` with reproducible `random_state`, calibrated $0-100$ scoring, prototype risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and a transparent composite risk scorer ($40\%$ ML $+ 40\%$ Graph $+ 20\%$ Behavioral).
- **`ml/inference.py`**: Complete pipeline runner with auditable, metric-grounded evidence generation.
- **`ml/investigator.py`**: AI Investigator case briefing for every account (typology, summary, key findings, next steps, linked accounts), built only from the computed evidence, so it works offline.
- **`backend/src/investigator.js`**: Optional Claude narrative. With `ANTHROPIC_API_KEY` set, `GET /api/investigate/:id` asks Claude to rewrite the briefing as an analyst narrative using only the pipeline's facts; without a key, or on any error, it returns the rule-based briefing.
- **`data/synthetic/generator.py`**: Synthetic transaction generator supporting controlled scenarios (`NORMAL`, `FAN_IN`, `FAN_OUT`, `RAPID_MOVEMENT`, `CHAIN`, `CIRCULAR_FLOW`, `COORDINATED_NETWORK`, `STRUCTURING`, `MULE_RING`).

---

## 3. Getting Started & Commands

### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Packages: `networkx`, `pandas`, `numpy`, `scikit-learn`, `pytest`

### Installation
```bash
pip install networkx pandas numpy scikit-learn pytest
```

### 1. Generate Synthetic Transactions
```bash
python data/synthetic/generator.py
```
*Outputs `data/synthetic/transactions_sample.json` containing 190 synthetic transactions across 73 accounts covering normal and anomalous scenarios.*

### 2. Run Graph Analysis Engine
```bash
python graph-engine/engine.py
```
*Constructs the NetworkX directed graph, runs all 7 topology detectors, extracts graph features, and prints summary metrics.*

### 3. Run Full ML & Risk Pipeline
```bash
python ml/inference.py
```
*Executes the complete pipeline: validation $\to$ graph analysis $\to$ feature engineering $\to$ Isolation Forest $\to$ risk scoring $\to$ evidence generation.*

### 4. Run Synthetic Scenario Benchmark Evaluation
```bash
python evaluate_benchmark.py
```
*Evaluates detection and risk scoring across all 9 controlled scenarios: NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK, STRUCTURING, MULE_RING.*

### 5. Run Complete Pytest Suite
```bash
python -m pytest tests/ -v
```
*Executes 50 unit, integration, benchmark, security, and regression tests.*

### 6. Run the Full Stack with Docker
```bash
docker compose up --build        # Docker Compose v2
docker-compose up --build        # older Compose v1
```
*Starts the dashboard on port 3001, the backend API on 5001, the graph engine on 8000 (`/docs`, `/health`, `POST /analyze`) and the ML engine on 8001 (`/docs`, `/health`, `POST /pipeline`). The frontend proxies `/api` to the backend.*

*Optional: `export ANTHROPIC_API_KEY=...` before starting to let Claude write AI Investigator narratives. Never commit the key; without it the dashboard uses the rule-based briefing.*

### 7. Regenerate the Dashboard's Offline Data
```bash
python data/synthetic/generator.py
python backend/engine_adapter.py --out frontend/public/data/initial_state.json
```
*The dashboard falls back to this file when the backend is unreachable, so regenerate it after changing detection or scoring logic.*

---

## 4. Test Suite Coverage

| Test File | Focus Area | Test Count | Status |
| :--- | :--- | :--- | :--- |
| **`tests/test_graph.py`** | Graph construction, node/edge attributes, timestamp robustness, Fan-In, Fan-Out, Circular Flows, Chains, Rapid Movement, Coordinated Networks, Graph Features | 13 tests | **PASSED** |
| **`tests/test_ml.py`** | Behavioral features, combined vector merging, Isolation Forest fitting, anomaly scores, normalized risk scores, reproducibility, risk levels, evidence generation | 8 tests | **PASSED** |
| **`tests/test_scenarios_benchmark.py`** | Controlled scenario evaluations (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK, STRUCTURING, MULE_RING), deterministic reproducibility, [0, 100] bounds | 11 tests | **PASSED** |
| **`tests/test_security.py`** | Missing fields, invalid account IDs, self-transfers, negative amounts, zero amounts, NaN/Inf, extreme value limits, invalid timestamps, malformed types, duplicate IDs, empty datasets, strict exception raising | 12 tests | **PASSED** |
| **`tests/test_regressions.py`** | Mixed-timezone timestamps, identical risk scores across Python hash seeds | 2 tests | **PASSED** |
| **`tests/test_upgrade.py`** | Structuring detector, rejection of out-of-order loops, AI Investigator briefing built from evidence | 4 tests | **PASSED** |
| **Total** | Full Layer Test Coverage | **50 tests** | **100% PASSED** |


---

## 5. Member 1 Integration Contract

Member 1 can consume the entire pipeline with a single import:

```python
from ml.inference import run_pipeline

results = run_pipeline(transactions)
# Returns structured dictionary matching docs/api-contract.md
```

Detailed JSON schema, payload specifications, and sample responses are documented in [docs/api-contract.md](docs/api-contract.md).  
Pipeline architecture and boundaries are documented in [docs/architecture.md](docs/architecture.md).

---

## 6. Disclaimer
This software is a synthetic-data hackathon prototype for algorithm research and demonstration. The topological patterns, risk scores, and risk tiers do **NOT** prove financial crime, do **NOT** constitute legal or regulatory evidence, and do **NOT** represent official banking compliance standards.

## Phase 2 additions

Everything below was added after the Phase 1 judge feedback. The measured numbers live in
[`docs/PHASE2_METRICS.md`](docs/PHASE2_METRICS.md), which is generated by the scripts and never typed by hand.

| Area | What was added | Where |
|---|---|---|
| Analyst workflow | Sign-in, case management (open, notes, escalate, decide), exportable STR/SAR-style report | `backend/src/cases.js`, `backend/src/report.js`, Cases tab |
| Access control | Two roles (AML analyst, compliance officer) with a permission matrix; only a compliance officer can file or close a case | `backend/src/auth.js` |
| Audit | Append-only audit log where each entry stores the SHA-256 hash of the previous one; tampering is detected | `backend/src/audit.js`, Audit Log tab |
| Privacy | KYC profile masked in every response; reveal needs the compliance role and a written reason, and is audited | `backend/src/privacy.js` |
| Data | Labelled synthetic Bangladesh-style MFS network generator (about 137,000 transactions per network, six typologies plus legitimate look-alikes) | `data/synthetic/mfs_generator.py` |
| Temporal graph | Time-ordered flow tracing: follows money hop by hop, finds flow chains and loops in one pass | `ml/temporal_flow.py` |
| Features | 83 features per account: transactional, temporal, graph, 2-hop neighbourhood, account type | `ml/feature_store.py` |
| Models | Trained gradient-boosting classifier with per-account drivers, compared against rules, graph detectors, IsolationForest and a random forest | `ml/supervised.py`, `ml/evaluation.py` |
| Account takeover | Risk-area detector scored against each customer's own baseline (usual areas, handset, spending); residents of a risk area are not flagged | `ml/context_risk.py`, `data/config/risk_areas.json` |
| Hundi | Detector for recurring informal remittance payout through an agent or wallet; licensed remittance payout is excluded | `ml/context_risk.py` |
| Fairness | Bias check across account tiers and districts; the score is now tier-aware | `ml/evaluation.py`, `ml/model.py` |
| Scale | Throughput and latency benchmark up to about one million transactions | `ml/benchmark.py` |

### Running it

```bash
docker-compose down && docker-compose up -d --build   # dashboard on http://localhost:3001
```

Open the dashboard and sign in with one of the two demo buttons (AML Analyst or Compliance Officer).
For password sign-in or to turn demo sign-in off, copy `.env.example` to `.env`.

### Tests and evaluation

```bash
python -m pytest -q            # 71 Python tests
cd backend && npm test         # 10 API tests: auth, roles, masking, audit chain, case workflow
python -m ml.evaluation        # model comparison, bias check (about 6 minutes)
python -m ml.benchmark --api http://localhost:5001   # throughput and API latency
```

### Honest limits

All data is synthetic and the simulator was written by the same team as the detectors, so the
reported accuracy is an upper bound. There is no upay integration, no real transaction data and
no analyst pilot yet. Neo4j/Kafka streaming and a trained GNN are planned, not built.
