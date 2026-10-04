# Member 1 Integration Contract: Graph & ML Risk Engine

> **Version:** 1.0.0  
> **Target Consumer:** Member 1 (Product, Backend API, Frontend Dashboard, Integration)  
> **Provider:** Member 2 (Graph Algorithms & Network Detection) & Member 3 (ML Anomaly Detection, Risk Scoring & Security)  
> **Status:** Final & Verified

---

## 1. Overview & Boundaries

This contract defines the structured JSON data models and Python callable entry points provided by the **Graph Engine** and **ML Risk Layer**.

- **Member 2 / Member 3 Scope:**
  - Ingestion validation & data cleaning
  - NetworkX graph construction & topology analysis
  - Suspicious pattern detection (Fan-In, Fan-Out, Rapid Passthrough, Chains, Circular Flows, Coordinated Networks)
  - Unsupervised Anomaly Detection (Isolation Forest)
  - Explainable Multi-Signal Risk Scoring (0–100)
  - Rule & Metric Grounded Evidence Generation
- **Member 1 Scope (Backend/Frontend):**
  - Member 1 can call `run_pipeline(transactions)` directly in Python, or wrap it in their Express / Node / FastAPI backend to serve REST/GraphQL endpoints for the React frontend dashboard.

---

## 2. Input Transaction Schema

The engine accepts a list of transaction dictionaries or a Pandas DataFrame.

### Schema Specification
| Field | Type | Required | Description | Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `transaction_id` | String | No (generated if absent) | Unique transaction identifier | Must be unique across batch |
| `sender_id` | String / Int | **Yes** | Originating account ID | Non-empty, cannot equal `receiver_id` |
| `receiver_id` | String / Int | **Yes** | Destination account ID | Non-empty, cannot equal `sender_id` |
| `amount` | Float / Int | **Yes** | Monetary transfer amount | Numeric, strictly `> 0`, no NaN/Inf, `< 1,000,000,000` |
| `timestamp` | String / Num | **Yes** | Time of transaction | ISO-8601 string or positive Unix epoch |

*Note: Fields `sender` and `receiver` are also accepted as aliases for `sender_id` and `receiver_id`.*

### Sample Input JSON
```json
[
  {
    "transaction_id": "TX_000001",
    "sender_id": "ACC_NORM_021",
    "receiver_id": "ACC_NORM_004",
    "amount": 250.50,
    "timestamp": "2026-03-01T09:10:23Z"
  },
  {
    "transaction_id": "TX_000002",
    "sender_id": "ACC_NORM_004",
    "receiver_id": "ACC_NORM_015",
    "amount": 240.00,
    "timestamp": "2026-03-01T09:15:00Z"
  }
]
```

---

## 3. Output Contract: `run_pipeline()`

### Top-Level Response Structure
```json
{
  "pipeline_status": "SUCCESS",
  "total_accounts_analyzed": 57,
  "validation_summary": {
    "is_valid": true,
    "valid_count": 156,
    "invalid_count": 0,
    "error_sample": []
  },
  "graph_summary": {
    "num_accounts": 57,
    "num_edges": 144,
    "is_directed": true,
    "density": 0.045113,
    "weakly_connected_components": 7,
    "strongly_connected_components": 28
  },
  "risk_distribution": {
    "LOW": 31,
    "MEDIUM": 25,
    "HIGH": 1,
    "CRITICAL": 0
  },
  "accounts": [
    {
      "account_id": "ACC_NORM_018",
      "risk_score": 77.4,
      "risk_level": "HIGH",
      "is_anomaly": true,
      "patterns": [
        "circular_flow",
        "rapid_movement"
      ],
      "scoring_breakdown": {
        "ml_component": 78.5,
        "graph_component": 65.0,
        "behavioral_component": 40.0
      },
      "evidence": [
        "Circular flow pattern detected: account participates in 39 directed cycle(s).",
        "Rapid fund movement detected: funds forwarded within 1603 seconds of receipt.",
        "Statistical multivariate anomaly flagged by Isolation Forest (anomaly score: 78.5/100)."
      ],
      "graph_features": {
        "in_degree": 4,
        "out_degree": 3,
        "total_degree": 7,
        "weighted_in_degree": 1240.50,
        "weighted_out_degree": 1180.00,
        "fan_in_score": 0.67,
        "fan_out_score": 0.38,
        "cycle_detected": 1,
        "cycle_count": 39,
        "chain_length": 4,
        "network_size": 25,
        "suspicious_neighbor_count": 3
      },
      "ml_features": {
        "transaction_count": 7,
        "total_incoming": 1240.50,
        "total_outgoing": 1180.00,
        "net_flow": 60.50,
        "average_transaction_amount": 345.79,
        "maximum_transaction_amount": 750.00,
        "transaction_velocity": 4.2,
        "incoming_outgoing_ratio": 1.05,
        "counterparty_diversity": 0.8571,
        "passthrough_ratio": 0.9512,
        "amount_volatility": 0.4215,
        "flow_imbalance_magnitude": 0.025
      }
    }
  ]
}

```

---

## 4. Account Risk Profile Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `account_id` | String | Account identifier |
| `risk_score` | Float | Normalized final composite risk score in range `[0.0, 100.0]` |
| `risk_level` | String | Risk tier: `"LOW"`, `"MEDIUM"`, `"HIGH"`, or `"CRITICAL"` |
| `is_anomaly` | Boolean | `true` if Isolation Forest classified account as outlier |
| `patterns` | Array[String] | Detected topological patterns: `fan_in`, `fan_out`, `circular_flow`, `transaction_chain`, `rapid_movement`, `coordinated_network` |
| `scoring_breakdown` | Object | Decomposed components: `ml_component`, `graph_component`, `behavioral_component` |
| `evidence` | Array[String] | Auditable, human-readable explanatory statements calculated from data |
| `graph_features` | Object | Topological NetworkX metrics |
| `ml_features` | Object | Behavioral metrics (volume, velocity, ratios) |

---

## 5. Python Integration Snippet for Member 1

Member 1 can consume the pipeline with a single import:

```python
from ml.inference import run_pipeline

# 1. Ingest transactions from file, database, or API request
transactions = [...] 

# 2. Run detection pipeline
result = run_pipeline(
    transactions=transactions,
    contamination=0.1,    # Expected outlier ratio (default 0.1)
    random_state=42,       # Guaranteed reproducibility
    strict_validation=False # True raises TransactionValidationError, False logs errors and filters
)

# 3. Access structured results
if result["pipeline_status"] == "SUCCESS":
    high_risk_accounts = [
        acc for acc in result["accounts"] 
        if acc["risk_level"] in ("HIGH", "CRITICAL")
    ]
    print(f"Detected {len(high_risk_accounts)} high-risk accounts.")
```

---

## 6. Risk Level Thresholds (Prototype Disclaimer)

| Risk Tier | Score Range | Definition |
| :--- | :--- | :--- |
| **LOW** | `[0.0, 40.0)` | Normal transactional behavior; no persistent pattern violations. |
| **MEDIUM** | `[40.0, 70.0)` | Mild anomaly or isolated pattern participation (e.g. single small cycle). |
| **HIGH** | `[70.0, 90.0)` | Multiple severe pattern matches (e.g., rapid passthrough + cycle + high velocity). |
| **CRITICAL** | `[90.0, 100.0]` | Extreme outlier in multivariate space with coordinated network involvement. |

> **IMPORTANT DISCLAIMER:** These risk thresholds are prototype engineering heuristics developed for hackathon evaluation and synthetic data benchmarks. They do **NOT** constitute regulatory AML thresholds, bank-approved credit/fraud scores, or legal determinations of financial crime.
