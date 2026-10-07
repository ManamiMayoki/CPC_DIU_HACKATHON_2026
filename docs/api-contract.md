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
Real output for the bundled sample (190 transactions). One account is shown and two lists are shortened with "...".

```json
{
  "pipeline_status": "SUCCESS",
  "total_accounts_analyzed": 73,
  "validation_summary": {
    "is_valid": true,
    "valid_count": 190,
    "invalid_count": 0,
    "error_sample": []
  },
  "graph_summary": {
    "num_accounts": 73,
    "num_edges": 162,
    "is_directed": true,
    "density": 0.030822,
    "weakly_connected_components": 9,
    "strongly_connected_components": 39
  },
  "risk_distribution": {
    "LOW": 56,
    "MEDIUM": 15,
    "HIGH": 0,
    "CRITICAL": 2
  },
  "accounts": [
    {
      "account_id": "ACC_MULE_CASHOUT",
      "risk_score": 94.74,
      "risk_level": "CRITICAL",
      "is_anomaly": true,
      "patterns": [
        "fan_in",
        "circular_flow",
        "transaction_chain",
        "rapid_movement",
        "structuring"
      ],
      "scoring_breakdown": {
        "ml_component": 95.84,
        "graph_component": 100.0,
        "behavioral_component": 82.0
      },
      "evidence": [
        "Circular flow pattern detected: funds travelled a 3-account loop (ACC_MULE_04 -> ACC_MULE_CASHOUT -> ACC_MULE_HUB -> ACC_MULE_04) and returned in 67 minutes with 90% of the value.",
        "Rapid fund movement detected: funds forwarded within 20 minutes of receipt.",
        "Fan-in pattern detected: received funds from 4 distinct senders with only 1 outgoing counterparties.",
        "Structuring detected: received 8 transactions just under the 10,000 threshold (total 72,469) within 24 hours.",
        "Transaction chain detected: participates in a multi-hop path spanning 3 hops.",
        "High transaction velocity: 10.8 transactions per hour.",
        "Severe fund imbalance: incoming funds exceed outgoing by 8.5x.",
        "High network exposure: directly connected to 5 accounts with flagged patterns.",
        "Statistical multivariate anomaly flagged by Isolation Forest (anomaly score: 95.84/100)."
      ],
      "graph_features": {
        "in_degree": 4.0,
        "out_degree": 1.0,
        "total_degree": 5.0,
        "weighted_in_degree": 72469.46,
        "weighted_out_degree": 8478.99,
        "fan_in_score": 1.0,
        "fan_out_score": 0.0,
        "cycle_detected": 1.0,
        "cycle_count": 4.0,
        "chain_length": 3.0,
        "structuring_detected": 1.0,
        "near_threshold_tx_count": 8.0,
        "network_size": 14.0,
        "suspicious_neighbor_count": 5.0
      },
      "ml_features": {
        "transaction_count": 9.0,
        "total_incoming": 72469.46,
        "total_outgoing": 8478.99,
        "net_flow": 63990.47,
        "average_transaction_amount": 8994.2722,
        "maximum_transaction_amount": 9410.75,
        "transaction_velocity": 10.8,
        "incoming_outgoing_ratio": 8.5459,
        "counterparty_diversity": 0.5556,
        "passthrough_ratio": 0.117,
        "amount_volatility": 0.032,
        "flow_imbalance_magnitude": 0.7905
      },
      "investigation": {
        "account_id": "ACC_MULE_CASHOUT",
        "headline": "Money-mule collection hub: ACC_MULE_CASHOUT",
        "typology": "Money-mule collection hub",
        "summary": "ACC_MULE_CASHOUT scores 94.7/100 (CRITICAL). It collects split deposits from many wallets and forwards them almost immediately. Detected patterns: fan-in collection, circular flow, multi-hop chain, rapid pass-through, structuring. Received BDT 72,469 and sent BDT 8,479 across 9 transactions.",
        "key_findings": [
          "Received 8 transfers just under BDT 10,000, totalling BDT 72,469 within 24 hours.",
          "Received money from 4 different wallets, all within two hours.",
          "Passed received money straight on once (to 1 wallet), the fastest within 20 minutes of receipt.",
          "Money went around the loop ACC_MULE_04 -> ACC_MULE_CASHOUT -> ACC_MULE_HUB -> ACC_MULE_04 in 67 minutes and 90% of it came back.",
          "Part of a transfer chain spanning 3 hops.",
          "The Isolation Forest model ranks its overall behaviour as a statistical outlier (ML score 96/100)."
        ],
        "next_steps": [
          "Pull the full list of near-threshold transfers and check whether one person controls the sending wallets (same NID, device or SIM).",
          "Compare the combined amount with the account's declared income or business profile.",
          "Identify the sending wallets and check how recently they were opened and whether they share a device, SIM or agent.",
          "..."
        ],
        "related_accounts": [
          "ACC_MULE_01",
          "ACC_MULE_02",
          "ACC_MULE_03",
          "ACC_MULE_04",
          "..."
        ],
        "caveat": "Generated from synthetic data and computed metrics. These are risk indicators for prioritisation, not proof of wrongdoing.",
        "generated_by": "rule-based"
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
| `patterns` | Array[String] | Detected topological patterns: `fan_in`, `fan_out`, `circular_flow`, `transaction_chain`, `rapid_movement`, `structuring`, `coordinated_network` |
| `scoring_breakdown` | Object | Decomposed components: `ml_component`, `graph_component`, `behavioral_component` |
| `evidence` | Array[String] | Auditable, human-readable explanatory statements calculated from data |
| `graph_features` | Object | Topological NetworkX metrics |
| `ml_features` | Object | Behavioral metrics (volume, velocity, ratios) |
| `investigation` | Object | AI Investigator case briefing built from the evidence: `headline`, `typology`, `summary`, `key_findings`, `next_steps`, `related_accounts`, `caveat`, `generated_by` (`"rule-based"`) |

### Backend endpoint: `GET /api/investigate/:accountId`

Returns `{ "success": true, "investigation": {...}, "source": "claude" | "rule-based", "note": string | null }`.
When the backend has `ANTHROPIC_API_KEY` set, Claude rewrites the briefing using only the account's computed facts (`source: "claude"`, cached per account until the dataset changes). Without a key, or if the call fails or is declined, the rule-based briefing is returned and `note` says why.

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
