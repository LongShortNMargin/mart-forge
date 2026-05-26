---
name: mart-dqc
description: "Phase D -- run data quality checks against the mart, score results across 8 control classes, and produce a DQC scorecard"
user-invocable: true
---

# mart-dqc -- Phase D: Data Quality Control

## When to use

Invoke this skill after `/mart-bootstrap` has generated the dbt scaffold and you
need to execute data quality checks, score the results, and produce a structured
scorecard. Use it for initial validation, regression testing, or periodic quality
audits.

## Prerequisites

- The dbt project scaffold exists (output of `/mart-bootstrap`).
- `mart.yml` has `phase` at `C_complete` or later.
- A dbt profile is configured and the target warehouse is accessible.
- `dbt deps` has been run (packages installed).

## Workflow

### Step 1 -- Run dbt test

Execute `dbt test` against the target environment. Capture the full output and
ensure `target/run_results.json` is generated.

If `dbt test` fails to execute (not test failures, but a runtime error), stop
and report the error. Do not proceed to scoring.

### Step 2 -- Parse run results

Read `target/run_results.json`. For each test result, extract:

- `test_name` -- the unique test identifier.
- `model` -- the model the test applies to.
- `status` -- pass / fail / warn / error.
- `execution_time` -- seconds.
- `failures` -- count of failing rows (if applicable).
- `message` -- failure detail message.

### Step 3 -- Classify into 8 control classes

Map each test to one of the 8 DQC control classes. Classification is based on
test type, naming convention, and the column/model it targets:

| # | Control Class | Description | Typical dbt tests |
|---|--------------|-------------|-------------------|
| 1 | **PK Integrity** | Primary keys are unique and not null | `unique`, `not_null` on PK columns |
| 2 | **FK Integrity** | Foreign keys reference valid parent records | `relationships` tests |
| 3 | **Freshness** | Source data meets SLA freshness requirements | `source_freshness`, custom recency tests |
| 4 | **Completeness / Volume** | Row counts are within expected bounds, no missing partitions | `row_count`, `not_null` on required fields, volume anomaly tests |
| 5 | **Accepted Ranges** | Values fall within business-valid ranges | `accepted_values`, custom range tests |
| 6 | **Duplicate Detection** | No unexpected duplicates at declared grain | `unique` on grain columns, `dbt_utils.unique_combination_of_columns` |
| 7 | **Null-Rate Threshold** | Null rates per column do not exceed thresholds | Custom null-rate tests, `dbt_expectations.expect_column_values_to_not_be_null` with threshold |
| 8 | **Business Reconciliation** | Aggregated values match expected totals from source systems | Singular tests comparing mart aggregates to source-of-truth values |

### Step 4 -- Check control catalog applicability

Not every control class applies to every table or metric. For each
(table, control_class) pair, determine applicability:

- **Applicable**: The control is relevant and a test exists.
- **Not applicable**: The control does not apply to this table. Document the
  rationale (e.g., "FK Integrity not applicable to seed tables with no foreign
  keys").
- **Missing**: The control applies but no test exists. Flag as a gap.

### Step 5 -- Score and produce scorecard

Calculate scores per control class and per model:

- **Pass rate**: `passed / (passed + failed + errored)` as a percentage.
- **Coverage**: `(applicable_with_test) / (applicable_total)` as a percentage.

Write `dqc_scorecard.json`:

```json
{
  "mart_name": "<string>",
  "run_at": "<ISO-8601>",
  "dbt_run_id": "<string from run_results>",
  "overall_pass_rate": "<float>",
  "overall_coverage": "<float>",
  "control_classes": [
    {
      "class_id": 1,
      "class_name": "PK Integrity",
      "applicable_count": "<int>",
      "tested_count": "<int>",
      "passed_count": "<int>",
      "failed_count": "<int>",
      "coverage": "<float>",
      "pass_rate": "<float>",
      "non_applicable": [
        {
          "model": "<string>",
          "rationale": "<string>"
        }
      ],
      "gaps": [
        {
          "model": "<string>",
          "description": "<string>"
        }
      ]
    }
  ],
  "model_scores": [
    {
      "model": "<string>",
      "layer": "ODS|DIM|DWD|DWS|ADS",
      "total_tests": "<int>",
      "passed": "<int>",
      "failed": "<int>",
      "warned": "<int>",
      "errored": "<int>",
      "pass_rate": "<float>"
    }
  ],
  "failures": [
    {
      "test_name": "<string>",
      "model": "<string>",
      "control_class": "<string>",
      "failure_count": "<int>",
      "message": "<string>"
    }
  ]
}
```

### Step 6 -- Update mart.yml

Set `phase` to `D_complete`. Add `last_dqc_run` timestamp and
`dqc_scorecard_path`.

### Step 7 -- Print summary

Display a summary table:

| Control Class | Coverage | Pass Rate | Gaps |
|--------------|----------|-----------|------|
| PK Integrity | 100% | 98% | 0 |
| ... | ... | ... | ... |
| **Overall** | **X%** | **Y%** | **N** |

Flag any control class with pass rate below 95% or coverage below 80% as
requiring attention.

## Output format

Primary artifact: `dqc_scorecard.json`.
Secondary: updated `mart.yml`, console summary.

## NOT for

- Generating the dbt project (use `/mart-bootstrap`).
- Fixing failing tests (manual remediation, then re-run `/mart-dqc`).
- Reviewing BRD/TDD quality (use `/mart-review`).
- Writing new tests -- this skill runs and scores existing tests only.
