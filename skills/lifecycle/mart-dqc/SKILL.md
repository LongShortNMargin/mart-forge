---
name: mart-dqc
description: "Phase D — run data quality checks against the mart, score results across 8 control classes, and produce a DQC scorecard"
user-invocable: true
---

# mart-dqc — Phase D: Data Quality Contract execution

## When to use

Invoke this skill after `mart-bootstrap` has produced a scaffolded
warehouse and you need to (a) run all dbt tests, (b) generate
`dqc_scorecard.json` from the results, and (c) update
`coverage_manifest.json` with verified metric counts.

## Prerequisites

- A working dbt project under `models/` with `dbt_project.yml`.
- `profiles.yml` configured (live or fixture mode).
- `docs/tech-design-doc.md` carries the DQC plan (T-18) and test case
  inventory (T-19).
- `mart.yml` has `phase: C_complete`.

## Hard gate

```
GATE: Scaffold (Phase C) must be present before DQC can run.
```

If `models/` is empty or `mart.yml` shows `phase` is not `C_complete`,
reject:

```
BLOCKED: Scaffold required before DQC.
Run /mart-bootstrap to complete Phase C.
```

## Workflow

### Step 1 — Run dbt build

```
dbt deps
dbt seed
dbt run
dbt test
```

If any step fails, stop and report. `dbt test` failures DO continue —
the failure is the signal the scorecard captures.

### Step 2 — Read run results

Read `target/run_results.json`. For each test result, extract:
- `unique_id` (e.g., `test.my_proj.unique_gme_dwd_option_contract_di_option_symbol`).
- `status` (`pass`, `error`, `fail`, `warn`).
- `execution_time`.

### Step 3 — Link tests to controls

For every DQC control declared in T-18 of the TDD, find the linked dbt
tests by naming convention:

| Control class | Test name pattern |
|---------------|------------------|
| PK Integrity | `unique_<model>_<pk>` and `not_null_<model>_<pk>` |
| FK Integrity | `relationships_<model>_<fk>_<dim>_<dim_pk>` |
| Freshness | `<model>_freshness` (singular) |
| Completeness / Volume | `<model>_volume` (singular) |
| Accepted Ranges | `accepted_range_<model>_<column>` |
| Duplicate Detection | `<model>_no_dupes` (singular) |
| Null-Rate Threshold | `<model>_<column>_null_rate` (singular) |
| Business Reconciliation | `<model>_recon_<external>` (singular) |

A control's status is derived from the union of its linked tests:
- All pass → `pass`.
- Any `error`-severity test fails → `error`.
- Only `warn`-severity tests fail → `warn`.
- No linked tests → `pending` (must be resolved before sign-off).
- `not_applicable` is set only by explicit T-18 declaration with
  rationale.

### Step 4 — Write dqc_scorecard.json

Schema (see `docs/dqc-framework.md`):

```json
{
  "mart": "<mart-name>",
  "generated_at": "<ISO-8601>",
  "controls": [
    {
      "id": "pk_integrity_dwd_orders",
      "control_class": "PK Integrity",
      "table": "gme_dwd_orders",
      "status": "pass",
      "linked_dbt_tests": ["unique_gme_dwd_orders_order_sk", "not_null_gme_dwd_orders_order_sk"],
      "last_dbt_run": "<ISO-8601>",
      "rationale": null,
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

Non-pass statuses MUST carry `attempts[]` per SPEC §6.3.

### Step 5 — Update coverage manifest

Update `coverage_manifest.json`:
- For each metric in the BRD, set `status` based on the linked control
  outcome.
- Recompute `verified_count` and `coverage_pct`.

### Step 6 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "mart-dqc", "input_artifact": "target/run_results.json", "output_artifact": "dqc_scorecard.json", "checkpoint": "D_complete", "reconstructed": false}
```

### Step 7 — Print summary

```
DQC Run Complete
  pass:           N
  warn:           N
  error:          N
  not_applicable: N
  pending:        N
Coverage: verified_count/planned_count = X/Y (Z%)
```

If `error > 0` or `pending > 0`, the mart is NOT ready to merge. Report
the failing controls with their linked dbt tests.

## Output format

Primary artifacts: `dqc_scorecard.json`, updated `coverage_manifest.json`.
Secondary: appended `.skill-invocations.jsonl`.

## NOT for

- Scaffolding (use `/mart-bootstrap`).
- Authoring tests by hand (tests are declared in T-19 of the TDD).
- Reviewing the mart holistically (use `/mart-review`).
