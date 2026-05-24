# Data Quality Contract (DQC) Framework

## Overview

DQC is structured as a **required control catalog**, not minimum test counts. Every mart must address all 8 control classes. Controls that don't apply to a specific table require a `not_applicable` entry with rationale.

## Control Catalog

### 1. PK Integrity
**What:** Primary key is not null and unique across all rows.
**Severity:** `error` (blocks pipeline)
**Implementation:** Generic dbt tests: `not_null` + `unique` on every PK column.
**Applicability:** All tables.

### 2. FK Integrity
**What:** Every foreign key resolves to a dimension row (including unknown member).
**Severity:** `error`
**Implementation:** Generic `relationships` test to each referenced DIM table.
**Applicability:** Tables with foreign keys only.

### 3. Freshness
**What:** Most recent `pull_ts_utc` is within expected SLA.
**Severity:** `error`
**Implementation:** Source freshness or singular test: `max(pull_ts_utc) > current_timestamp - interval '{sla}'`.
**Applicability:** ODS and DWD tables.

### 4. Completeness / Volume
**What:** Row count is within expected range vs prior run.
**Severity:** `warn`
**Implementation:** Singular test comparing today's count to yesterday's, fail if delta > configurable threshold (default 50%).
**Applicability:** All tables with regular refresh.

### 5. Accepted Ranges
**What:** Numeric metrics within plausible bounds.
**Severity:** `warn`
**Implementation:** Generic `accepted_values` for enums; singular tests for numeric range checks.
**Applicability:** Native and derived numeric metrics.

### 6. Duplicate Detection
**What:** No duplicate business keys within a grain window.
**Severity:** `error`
**Implementation:** Singular test: `GROUP BY business_key HAVING COUNT(*) > 1`.
**Applicability:** All fact tables.

### 7. Null-Rate Threshold
**What:** Non-PK columns do not exceed configured null percentage.
**Severity:** `warn`
**Implementation:** Singular test: `COUNT(*) FILTER (WHERE col IS NULL) / COUNT(*) > threshold`.
**Applicability:** All tables (threshold configured per column).

### 8. Business Reconciliation
**What:** Key metrics match external source within tolerance.
**Severity:** `error` or `warn`
**Implementation:** Singular test comparing mart output to external reference value.
**Applicability:** Required only when an exact, semantically valid external comparator exists. Proxy sources do NOT satisfy this requirement.

## Applicability by Source Type

| Source Type | Required Controls | Reconciliation Rule |
|-------------|-------------------|---------------------|
| `native` | PK, provenance, freshness, pass-through checks | Identity/provenance/freshness only |
| `derived` | PK, formula/logic tests, accepted ranges | SQL/formula validation per TDD |
| `hybrid` | PK, provenance, formula tests, reconciliation | Component split + tolerance |

## Scorecard

The `dqc_scorecard.json` artifact is mechanically generated from `dbt test` results via `scripts/dqc_update.py`.

### Schema

```json
{
  "mart": "mart-name",
  "generated_at": "ISO-8601",
  "controls": [
    {
      "class": "pk_integrity",
      "metric": "order_id",
      "status": "pass",
      "linked_dbt_tests": ["test_pk_not_null", "test_pk_unique"],
      "last_dbt_run": "ISO-8601"
    },
    {
      "class": "business_reconciliation",
      "metric": "total_revenue",
      "status": "exhausted",
      "attempts": [
        {"source": "provider_a", "result": "blocked", "reason": "Paid API", "date": "2026-01-01"}
      ],
      "linked_dbt_tests": [],
      "last_dbt_run": "ISO-8601"
    }
  ]
}
```

### Status Values

- `pass` — within tolerance
- `fail` — outside tolerance (blocks pipeline if severity = error)
- `exhausted` — all resources attempted, none verified. NOT a pass. Requires `attempts[]`.
- `not_applicable` — control doesn't apply to this table/metric. Requires rationale.

## Resource Exhaustion Protocol

Before marking any control `exhausted`:
1. Enumerate all resources from BRD + candidate sources
2. Attempt each: document source, result (pass/blocked/error), reason, date, evidence
3. Only after ALL attempted can `exhausted` be assigned
