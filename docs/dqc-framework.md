# DQC Framework — 8-Control Quality Catalog

## Overview

The Data Quality Control (DQC) framework defines 8 controls that validate every
model in a mart-forge pipeline. Controls are applied automatically by the
`/mart-dqc` skill based on table type, layer, and configuration in `mart.yml`.
Each control has a defined severity, applicability scope, and mapping to dbt tests.

## Control Catalog

### Control 1: PK Integrity

**Definition:** The declared primary key is not null and unique across all rows.

- **Severity:** error
- **Applicability:** All tables, all layers.
- **dbt Test:** `dbt_utils.unique_combination_of_columns` or built-in `unique` + `not_null`.
- **Failure Impact:** Pipeline halt. A PK violation means the grain contract is broken.

**Implementation:**
```yaml
# mart.yml
columns:
  - name: instrument_sk
    tests:
      - unique
      - not_null
```

---

### Control 2: FK Integrity

**Definition:** Every foreign key value resolves to an existing row in the
referenced dimension table.

- **Severity:** error
- **Applicability:** Tables with foreign key references only (DWD, DWS, ADS).
- **dbt Test:** `relationships` test pointing to the parent dimension.
- **Failure Impact:** Pipeline halt. Orphaned FKs produce NULL joins in downstream tables.

**Implementation:**
```yaml
columns:
  - name: instrument_sk
    tests:
      - relationships:
          to: ref('dim_instrument')
          field: instrument_sk
```

---

### Control 3: Freshness

**Definition:** The most recent `pull_ts_utc` value is within the configured SLA
window for the provider.

- **Severity:** error
- **Applicability:** ODS and DWD tables (tables with `pull_ts_utc` column).
- **dbt Test:** `dbt source freshness` or custom macro checking max(pull_ts_utc).
- **Failure Impact:** Pipeline halt. Stale data produces misleading downstream metrics.

**Configuration:**
```yaml
freshness:
  warn_after: {count: 2, period: hour}
  error_after: {count: 6, period: hour}
loaded_at_field: pull_ts_utc
```

---

### Control 4: Completeness / Volume

**Definition:** Row count for the current run is within an expected range compared
to the prior run. Detects both data loss (too few rows) and duplication (too many).

- **Severity:** warn
- **Applicability:** Tables with regular refresh cadence (ODS, DWD, DWS).
- **dbt Test:** Custom macro comparing `count(*)` between current and prior run.
- **Failure Impact:** Warning. Investigate manually — could be legitimate volatility.

**Thresholds:**
```yaml
volume:
  min_pct_of_prior: 80    # warn if row count drops below 80% of last run
  max_pct_of_prior: 150   # warn if row count exceeds 150% of last run
```

---

### Control 5: Accepted Ranges

**Definition:** Numeric metric columns fall within plausible bounds. Catches
data corruption, unit-of-measure errors, and decimal-point shifts.

- **Severity:** warn
- **Applicability:** Native and derived numeric metric columns (DWD, DWS).
- **dbt Test:** `dbt_utils.accepted_range` or custom range macro.
- **Failure Impact:** Warning. Out-of-range values are flagged but not removed.

**Configuration:**
```yaml
columns:
  - name: close_price
    tests:
      - dbt_utils.accepted_range:
          min_value: 0
          max_value: 1000000
  - name: volume
    tests:
      - dbt_utils.accepted_range:
          min_value: 0
```

---

### Control 6: Duplicate Detection

**Definition:** No duplicate rows exist within the declared grain window. The
grain key (business key + grain columns) must be unique.

- **Severity:** error
- **Applicability:** All fact tables (ODS, DWD, DWS).
- **dbt Test:** `dbt_utils.unique_combination_of_columns` on the grain key set.
- **Failure Impact:** Pipeline halt. Duplicates inflate aggregations downstream.

**Implementation:**
```yaml
tests:
  - dbt_utils.unique_combination_of_columns:
      combination_of_columns:
        - instrument_bk
        - trade_date
        - provider
```

---

### Control 7: Null-Rate Threshold

**Definition:** Non-PK columns do not exceed a configured null percentage. Catches
ingestion failures where a provider returns empty fields.

- **Severity:** warn
- **Applicability:** All tables, all layers. Threshold configured per column.
- **dbt Test:** Custom macro computing `count(*) filter (where col is null) / count(*)`.
- **Failure Impact:** Warning. High null rates are logged to the scorecard.

**Configuration:**
```yaml
columns:
  - name: close_price
    meta:
      null_threshold_pct: 5    # warn if more than 5% null
  - name: dividend_amount
    meta:
      null_threshold_pct: 90   # optional column, high null is expected
```

---

### Control 8: Business Reconciliation

**Definition:** Key metrics computed by the pipeline match an external source of
truth within a configured tolerance. The gold standard for end-to-end correctness.

- **Severity:** error or warn (configurable per metric)
- **Applicability:** Only when an exact external comparator exists.
- **dbt Test:** Custom reconciliation macro comparing pipeline output to a reference table.
- **Failure Impact:** Depends on severity setting. Error halts; warn logs to scorecard.

**Configuration:**
```yaml
reconciliation:
  - metric: total_volume
    external_source: ref('recon_volume_external')
    tolerance_pct: 1.0
    severity: error
  - metric: avg_close_price
    external_source: ref('recon_price_external')
    tolerance_pct: 0.5
    severity: warn
```

## Applicability Matrix by Source Type

Controls apply differently depending on the column's `source_type`:

| Control                   | native | derived | hybrid |
|---------------------------|:------:|:-------:|:------:|
| 1. PK Integrity           |   X    |    X    |   X    |
| 2. FK Integrity           |   X    |    X    |   X    |
| 3. Freshness              |   X    |    -    |   X    |
| 4. Completeness/Volume    |   X    |    X    |   X    |
| 5. Accepted Ranges        |   X    |    X    |   X    |
| 6. Duplicate Detection    |   X    |    X    |   X    |
| 7. Null-Rate Threshold    |   X    |    X    |   X    |
| 8. Business Reconciliation|   X    |    X    |   X    |

**Notes:**
- `native`: Pass-through from source. Freshness applies because it depends on provider SLA.
- `derived`: Computed via SQL expression. Freshness is N/A (derived from already-fresh inputs).
- `hybrid`: Contains both native and derived columns. Freshness checked on native subset.

## Severity Rules

| Severity | Pipeline Effect              | Scorecard Effect         |
|----------|------------------------------|--------------------------|
| `error`  | Pipeline halts, run fails    | Red flag, blocks sign-off |
| `warn`   | Pipeline continues           | Yellow flag, logged       |

Severity escalation: a `warn` control that fires on 3 consecutive runs is
automatically escalated to `error` on the 4th run. This prevents persistent
warnings from being ignored.

## How Controls Link to dbt Tests

Each control maps to one or more dbt test types:

| Control              | dbt Test Type                            |
|----------------------|------------------------------------------|
| PK Integrity         | `unique`, `not_null`                     |
| FK Integrity         | `relationships`                          |
| Freshness            | `source freshness`                       |
| Completeness/Volume  | Custom macro (`mart_forge_volume_check`) |
| Accepted Ranges      | `dbt_utils.accepted_range`               |
| Duplicate Detection  | `dbt_utils.unique_combination_of_columns`|
| Null-Rate Threshold  | Custom macro (`mart_forge_null_rate`)    |
| Business Reconciliation | Custom macro (`mart_forge_reconcile`) |

mart-forge ships macros for controls 4, 7, and 8. Controls 1, 2, 3, 5, and 6
use standard dbt and dbt_utils tests.

## Scorecard Schema

Every DQC run produces a scorecard record:

```json
{
  "run_id": "abc123",
  "run_ts_utc": "2025-01-15T08:30:00Z",
  "model": "gme_dwd_options_daily",
  "controls": [
    {"id": 1, "name": "pk_integrity", "status": "pass", "severity": "error"},
    {"id": 4, "name": "completeness", "status": "warn", "severity": "warn",
     "detail": "row_count=1842, prior=2105, pct=87.5"},
    {"id": 7, "name": "null_rate", "status": "pass", "severity": "warn"}
  ],
  "overall": "warn",
  "error_count": 0,
  "warn_count": 1
}
```

Scorecards are stored in `target/dqc_scorecards/` and can be aggregated for
trend analysis across runs.
