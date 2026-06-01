---
name: 8-control-dqc-audit
description: "Audit a mart against the eight DQC control classes (PK / FK / Freshness / Volume / Ranges / Duplicates / Null-Rate / Reconciliation) and produce a scorecard that names the gaps and the remediation owner"
user-invocable: true
---

# 8-control-dqc-audit — Eight-Control DQC Audit

## When to use

Invoke this skill when:

- A new mart is about to be promoted past the in-review gate.
- A signed TDD has shipped and the DWS/ADS models have run at least once.
- A pre-existing mart needs its scorecard refreshed (quarterly review,
  schema-evolution event, or after an incident).

This is the operational counterpart to `mart-dqc`: `mart-dqc` scaffolds
the test files; this skill walks them and produces the gap report.

## Prerequisites

- A successful `dbt build` against the dev target.
- A populated `dqc_scorecard.json` (scaffolded by `mart-dqc`).
- The TDD §T-15 DQC matrix that names which controls apply per table.

## The eight controls

| # | Control                  | Pass criterion                                                  |
|---|--------------------------|-----------------------------------------------------------------|
| 1 | PK Integrity             | dbt `unique` + `not_null` tests on each declared PK.            |
| 2 | FK Integrity             | dbt `relationships` test on every FK column.                    |
| 3 | Freshness                | Max event timestamp within the SLA from TDD §T-13.              |
| 4 | Completeness / Volume    | Row count within ±N% of the rolling baseline (configurable).    |
| 5 | Accepted Ranges          | Numeric columns inside the declared bounds.                     |
| 6 | Duplicate Detection      | No duplicate business keys within the grain window.             |
| 7 | Null-Rate Threshold      | Each non-PK column under its declared null-rate ceiling.        |
| 8 | Business Reconciliation  | Variance against the external comparator within tolerance.      |

Controls that do not apply (e.g. no external comparator for a derived
metric) are marked `not_applicable` with a one-line rationale. They
are not silently skipped — an empty audit row is treated as `pending`.

## Workflow

### Step 1 — Collect linked tests

For every row in the TDD §T-15 matrix, find the dbt test(s) that
implement it. The naming convention is
`<control_class>_<table>_<column>` — e.g. `pk_integrity_dwd_orders`
links the `unique` and `not_null` tests on `dwd_orders.order_sk`.

Tests that exist but are not linked to a control row are surfaced as
**orphan tests** in the audit report — usually a sign the scorecard
is out of date.

### Step 2 — Read `target/run_results.json`

After `dbt test`, parse `run_results.json` for each linked test:

| dbt status               | scorecard status |
|--------------------------|------------------|
| `pass`                   | `pass`           |
| `warn`                   | `warn`           |
| `error` / `fail`         | `error`          |
| not in run_results       | `pending`        |

A control's overall status is the union: any `error` → `error`; else
any `warn` → `warn`; else if any `pending` → `pending`; else `pass`.

### Step 3 — Produce the scorecard delta

Compare the freshly-computed statuses against the committed
`dqc_scorecard.json`. Emit:

- **Regressions** — controls that moved from `pass` to `warn`/`error`.
- **Recoveries** — controls that moved up.
- **New tests** — orphan tests that need a control row.
- **Stale rows** — control rows whose `linked_dbt_tests` no longer
  exist in the project.

### Step 4 — Update the scorecard

Write the new scorecard. Every non-`pass` status MUST carry an
`attempts[]` array with at least one entry naming the date, the source
of the finding, and the proposed remediation owner. A bare `error`
row with no attempt history is rejected by the lint script in Step 5.

### Step 5 — Lint the scorecard

```sh
python scripts/lint_dqc_scorecard.py dqc_scorecard.json
```

The linter rejects:

- Controls with `status` in `{warn, error}` and empty `attempts`.
- Controls referencing `linked_dbt_tests` that do not exist.
- Summary counts that do not match the row-level statuses.

## Output format

- Updated `dqc_scorecard.json` with refreshed statuses and
  `attempts[]` entries for every non-pass row.
- A `docs/dqc-audit-<date>.md` report enumerating regressions,
  recoveries, orphan tests, and the next-action list per owner.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: 8-control-dqc-audit`, output_artifact =
  `dqc_scorecard.json`).
- Exit code 1 if any control is `error`-severity unresolved.

## NOT for

- Authoring new dbt tests (use `mart-dqc`).
- DuckDB-specific incremental controls (use `duckdb-incremental-models`).
- Cross-mart conformance audits.
- Naming or grain checks (use `naming-conventions-lint` /
  `grain-rules-check`).
