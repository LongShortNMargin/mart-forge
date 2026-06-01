---
name: grain-rules-check
description: "Enforce grain declaration discipline — every fact table declares its grain in mart.yml AND in a per-model SQL comment, and every join across grains either re-aggregates or is explicitly waived in TDD §T-7"
user-invocable: true
---

# grain-rules-check — Grain Discipline Check

## When to use

Run this skill:

- Right after `mart-bootstrap` scaffolds the DWD/DWS models.
- Whenever a reviewer flags a "double-counting" suspicion on a metric.
- Before promotion past in-review; an undeclared grain is the
  most-common-source of silent data bugs in a Kimball warehouse.

## Prerequisites

- A signed TDD with §T-7 declared (this is where intentional
  grain-crossing joins are documented and waived).
- A populated `mart.yml` with `tables.<name>.grain` for every fact
  table.
- At least one model exists under `models/dwd/` or `models/dws/`.

## The grain rule

Every fact-grade table (DWD and DWS) MUST declare its grain in two
places:

1. **`mart.yml`** — under `tables.<table_name>.grain`. The value is the
   shortest English phrase that names "one row =". Examples:
   - `one row per order line per second`
   - `one row per option contract per day`
   - `one row per session-strike per hour`
2. **The model SQL** — a leading comment block:
   ```sql
   -- grain: one row per option contract per day
   -- grain_keys: (contract_id, snapshot_date)
   ```

Mismatches between the two declarations are an error. Drifted grain
declarations are the early warning of a join that has silently
fanned out.

## What the check enforces

| Rule                                                                                                                | Severity |
|---------------------------------------------------------------------------------------------------------------------|----------|
| Every DWD / DWS table has `grain:` and `grain_keys:` in `mart.yml`                                                  | error    |
| Every DWD / DWS .sql file has both `-- grain:` and `-- grain_keys:` comment lines                                   | error    |
| The two declarations match exactly (case-sensitive)                                                                 | error    |
| Every join in the model is one of: same-grain inner / left, OR explicit re-aggregation, OR a TDD §T-7 waiver        | error    |
| ADS views inherit grain from their immediate DWS parent (no silent re-aggregation in ADS)                           | warn     |
| Grain phrases match the regex `^one row per .+?$` (forces a clear statement, not a hand-wave)                       | warn     |

## Detecting fan-out joins

The static check inspects every `JOIN` clause and flags a join as
**suspect** if:

- The right-hand table's grain is finer than the left-hand table's
  (e.g., `contract_per_day` JOIN `tick_per_second`), AND
- The JOIN's `ON` clause does not include the right-hand grain's full
  key set, AND
- The SELECT does not wrap the result in a `GROUP BY` matching the
  left-hand grain.

A flagged join is `error` unless the model carries a one-line
`-- grain_waiver: <ref to TDD §T-7 row>` comment pointing at the TDD
row that captured the intentional fan-out (e.g., a snapshot join that
keeps the finer grain on purpose).

## Workflow

### Step 1 — Read `mart.yml`

Build `{table -> (grain, grain_keys)}` from the manifest.

### Step 2 — Parse model SQL

For each `models/dwd/*.sql` and `models/dws/*.sql`, extract:

- The leading `-- grain:` and `-- grain_keys:` comments.
- The list of `JOIN` clauses with their `ON` keys.
- The presence and shape of the model's outer `GROUP BY`.

### Step 3 — Compare and report

Render a report grouped by severity:

```
[error] dwd_orders.sql
  - grain comment is missing
  - mart.yml declares "one row per order_line per second"; SQL is silent

[error] dws_session_strike_1d.sql
  - join into ods_tick fans grain finer; no GROUP BY rolls it back
  - either re-aggregate to one row per (session, strike, day)
    or add a -- grain_waiver: T-7.2 comment

[warn] ads_market_dashboard.sql
  - ADS view re-aggregates DWS; expected grain inheritance
```

Exit code 1 on any error.

## Output format

- Stdout report grouped by severity (error / warn).
- Per-file findings with rule + remediation pointer.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: grain-rules-check`, output_artifact = path to the
  saved report or to `models/`).
- Exit code 1 on any error.

## NOT for

- SCD-2 history grain (dimensions, not facts; separate review).
- Time-zone correctness inside grain phrases (caught by
  `naming-conventions-lint` via `_ts_utc` rule).
- Cross-mart grain conformance.
- Naming convention drift (use `naming-conventions-lint`).
