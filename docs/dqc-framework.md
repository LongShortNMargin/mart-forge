# Data Quality Contract (DQC) Framework

mart-forge enforces eight control classes on every warehouse. The classes
are catalogued here; the per-table applicability is decided in the TDD
and rendered to `dqc_scorecard.json`.

## The eight controls

| # | Control | What it checks | Severity | Applies to |
|---|---------|----------------|----------|-----------|
| 1 | PK Integrity | Primary key column is not null and unique | `error` | All tables |
| 2 | FK Integrity | Foreign key resolves to a row in the referenced dimension | `error` | Tables with foreign keys |
| 3 | Freshness | The most recent `pull_ts_utc` is within the table's SLA | `error` | ODS, DWD |
| 4 | Completeness / Volume | Row count is within an expected range vs the prior run | `warn` | Tables with regular refresh |
| 5 | Accepted Ranges | Numeric metrics fall within plausible bounds | `warn` | Numeric metric columns |
| 6 | Duplicate Detection | No duplicate business keys within the grain window | `error` | All fact tables |
| 7 | Null-Rate Threshold | Non-PK columns stay under a configured null percentage | `warn` | All tables (threshold per column) |
| 8 | Business Reconciliation | Key metrics match an external source within tolerance | `error` or `warn` | Only when an `exact` external comparator exists |

## Applicability by source type

| Source type | Required controls | Optional |
|-------------|------------------|----------|
| `native` | PK Integrity, Freshness, Provenance presence, Pass-through field checks | Accepted Ranges, Null-Rate |
| `derived` | PK Integrity, Formula/business-logic tests, Accepted Ranges | Null-Rate |
| `hybrid` | PK Integrity, Provenance presence, Formula tests, Documented reconciliation with tolerance | Accepted Ranges, Null-Rate |

Controls that do not apply to a particular table/metric are recorded in
the scorecard as `not_applicable` with a one-line rationale. They are
not silently skipped.

## Scorecard schema

`dqc_scorecard.json`:

```json
{
  "mart": "<mart-name>",
  "generated_at": "<ISO-8601>",
  "controls": [
    {
      "id": "pk_integrity_dwd_orders",
      "control_class": "PK Integrity",
      "table": "gme_dwd_orders",
      "status": "pass | warn | error | not_applicable | pending",
      "linked_dbt_tests": ["unique_gme_dwd_orders_order_sk", "not_null_gme_dwd_orders_order_sk"],
      "last_dbt_run": "<ISO-8601>",
      "rationale": "<for not_applicable, why this control does not apply>",
      "attempts": []
    }
  ],
  "summary": {
    "pass_count": 0,
    "warn_count": 0,
    "error_count": 0,
    "not_applicable_count": 0,
    "pending_count": 0
  }
}
```

The `attempts[]` array is required for any control with a non-`pass`
status. Each attempt is an object with `source`, `result`, `reason`,
`date`, `evidence_uri`.

## Linkage to `dbt test`

The scorecard is mechanically generated from `target/run_results.json`
after `dbt test`. The generation rules:

- Every dbt test that exists is linked to exactly one control row by
  naming convention.
- A control's `status` is derived from the union of its linked tests:
  - All pass → `pass`.
  - Any error-severity test fails → `error`.
  - Only warn-severity tests fail → `warn`.
- The `last_dbt_run` timestamp comes from `run_results.json`.
- A control with no linked tests has status `pending` until the test is
  added or the control is explicitly `not_applicable`.

## Display rules on the dashboard

`G-HONEST-LABEL` (SPEC §9) forbids displaying a non-pass status as
green. The dashboard renders:

| Status | Display |
|--------|---------|
| `pass` | Green check |
| `warn` | Yellow exclamation |
| `error` | Red X |
| `not_applicable` | Gray dash |
| `pending` | Blue hourglass |

The badge is rendered inline with the metric value. Removing the badge
component or making it conditional on truthy values is a CI failure.

## Referenced from

- `SPEC.md` §8.2 and §8.3.
- `templates/tests/*.sql`.
- `templates/dashboard/app.py` (renders the badges).
