# FlowGuard AI: Graph Detection & ML Risk Engine

> **CPC DIU HACKATHON 2026**  
> **Implemented Roles:**  
> - **MEMBER 2:** Graph Algorithms & Network Detection  
> - **MEMBER 3:** ML / Anomaly Detection, Risk Scoring & Security / Testing  
> *(Member 1 is responsible for Product, Frontend, Backend, Integration, and Presentation)*

---

## 1. Executive Summary

This repository hosts the core intelligence layer of **FlowGuard AI**—an end-to-end framework combining graph topology algorithms and unsupervised machine learning to detect suspicious financial transaction patterns on synthetic datasets.

```
Synthetic Transactions
        ↓
Transaction Validation (Security)
        ↓
NetworkX Transaction Graph
        ↓
Network Pattern Detection (Fan-In, Fan-Out, Cycles, Chains, Rapid Movement, Coordinated Networks)
        ↓
Graph Topological Features + ML Behavioral Features
        ↓
Isolation Forest Anomaly Detection
        ↓
Explainable Composite Risk Scoring (0–100)
        ↓
Grounded Evidence Generation
        ↓
Structured Integration Contract for Member 1
```

---

## 2. Implemented Architecture & Modules

### Member 2: Graph Algorithms & Network Detection
- **`graph-engine/graph.py`**: Builds NetworkX directed graphs (`nx.DiGraph` & `nx.MultiDiGraph`) with account nodes and transaction edges preserving amounts, timestamps, and IDs.
- **`graph-engine/patterns.py`**: Algorithmic detectors for 6 key suspicious patterns:
  1. **Fan-In**: Aggregation from multiple accounts to one collector.
  2. **Fan-Out**: Dispersion from one distributor to multiple accounts.
  3. **Circular Flows**: Directed cycles ($A \to B \to C \to A$) detecting potential layering loops.
  4. **Transaction Chains**: Multi-hop linear paths ($\ge 3$ hops).
  5. **Rapid Fund Movement**: Inflow followed by immediate comparable outflow within minutes.
  6. **Coordinated Networks**: Dense interconnected account clusters.
- **`graph-engine/features.py`**: Account-level graph feature extraction (`in_degree`, `out_degree`, `weighted_degrees`, `counterparties`, `cycle_count`, `chain_length`, `network_size`, `suspicious_neighbor_count`).
- **`graph-engine/engine.py`**: Graph analysis orchestrator.

### Member 3: ML Anomaly Detection, Risk Scoring & Security
- **`ml/validation.py`**: Rigorous data validation preventing negative/zero amounts, `NaN`, `Inf`, extreme values ($> 10^9$), invalid timestamps, self-transfers, duplicate transaction IDs, and malformed inputs.
- **`ml/features.py`**: Behavioral feature extraction (transaction counts, inflows/outflows, velocity, ratios) and merged ML feature vector creation.
- **`ml/model.py`**: Unsupervised anomaly detector using `IsolationForest` with reproducible `random_state`, calibrated $0-100$ scoring, prototype risk tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and a transparent composite risk scorer ($40\%$ ML $+ 40\%$ Graph $+ 20\%$ Behavioral).
- **`ml/inference.py`**: Complete pipeline runner with auditable, metric-grounded evidence generation.
- **`data/synthetic/generator.py`**: Synthetic transaction generator supporting controlled scenarios (`NORMAL`, `FAN_IN`, `FAN_OUT`, `RAPID_MOVEMENT`, `CHAIN`, `CIRCULAR_FLOW`, `COORDINATED_NETWORK`).

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
*Outputs `data/synthetic/transactions_sample.json` containing 156 synthetic transactions covering normal and anomalous scenarios.*

### 2. Run Graph Analysis Engine
```bash
python graph-engine/engine.py
```
*Constructs the NetworkX directed graph, runs all 6 topology detectors, extracts graph features, and prints summary metrics.*

### 3. Run Full ML & Risk Pipeline
```bash
python ml/inference.py
```
*Executes the complete pipeline: validation $\to$ graph analysis $\to$ feature engineering $\to$ Isolation Forest $\to$ risk scoring $\to$ evidence generation.*

### 4. Run Synthetic Scenario Benchmark Evaluation
```bash
python evaluate_benchmark.py
```
*Evaluates detection and risk scoring across all controlled scenarios: NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK.*

### 5. Run Complete Pytest Suite
```bash
python -m pytest tests/ -v
```
*Executes 42 unit, integration, benchmark, and security tests.*

---

## 4. Test Suite Coverage

| Test File | Focus Area | Test Count | Status |
| :--- | :--- | :--- | :--- |
| **`tests/test_graph.py`** | Graph construction, node/edge attributes, timestamp robustness, Fan-In, Fan-Out, Circular Flows, Chains, Rapid Movement, Coordinated Networks, Graph Features | 13 tests | **PASSED** |
| **`tests/test_ml.py`** | Behavioral features, combined vector merging, Isolation Forest fitting, anomaly scores, normalized risk scores, reproducibility, risk levels, evidence generation | 8 tests | **PASSED** |
| **`tests/test_scenarios_benchmark.py`** | Controlled scenario evaluations (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT, CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK), deterministic reproducibility, [0, 100] bounds | 9 tests | **PASSED** |
| **`tests/test_security.py`** | Missing fields, invalid account IDs, self-transfers, negative amounts, zero amounts, NaN/Inf, extreme value limits, invalid timestamps, malformed types, duplicate IDs, empty datasets, strict exception raising | 12 tests | **PASSED** |
| **Total** | Full Layer Test Coverage | **42 tests** | **100% PASSED** |


---

## 5. Member 1 Integration Contract

Member 1 can consume the entire pipeline with a single import:

```python
from ml.inference import run_pipeline

results = run_pipeline(transactions)
# Returns structured dictionary matching docs/api-contract.md
```

Detailed JSON schema, payload specifications, and sample responses are documented in [docs/api-contract.md](file:///b:/Ai%20hackthon/CPC_DIU_HACKATHON_2026/docs/api-contract.md).  
Pipeline architecture and boundaries are documented in [docs/architecture.md](file:///b:/Ai%20hackthon/CPC_DIU_HACKATHON_2026/docs/architecture.md).

---

## 6. Disclaimer
This software is a synthetic-data hackathon prototype for algorithm research and demonstration. The topological patterns, risk scores, and risk tiers do **NOT** prove financial crime, do **NOT** constitute legal or regulatory evidence, and do **NOT** represent official banking compliance standards.
