---
name: naming-conventions-lint
description: "Check that every dbt model and column name in a mart follows the documented ODS / DIM / DWD / DWS / ADS prefix-and-grain rules — flags renamed source leaks, missing layer markers, and column-suffix drift"
user-invocable: true
---

# naming-conventions-lint — Naming Conventions Lint

## When to use

Run this skill:

- After scaffolding a new mart (the bootstrap should not leave drift,
  but human edits in the same PR sometimes do).
- After `schema-evolve` propagates new columns.
- Before tagging a release — naming drift is the cheapest signal that
  someone bypassed the lifecycle.

## Prerequisites

- `mart.yml` declares `mart_name` (and optionally `mart_prefix` and
  `dims_are_conformed`).
- At least one model exists under `models/`.
- The mart has run `dbt parse` successfully (the linter does not
  re-parse SQL; it walks files).

## What it checks

### Model names

Each `.sql` model under `models/` must match
`<prefix>_<layer>_<noun>[_<grain>]`:

| Rule                                                                  | Severity |
|-----------------------------------------------------------------------|----------|
| ODS / DWD / DWS / ADS files carry the mart prefix from `mart.yml`     | error    |
| DIM files MUST NOT carry the mart prefix (conformed dims are shared)  | error    |
| Layer marker is one of `{ods, dim, dwd, dws, ads}`                    | error    |
| DWD / DWS grain suffix (`_di`, `_1d`, `_1h`, etc.) is present         | warn     |
| Noun contains no provider-specific token (`yfinance`, `cboe`)         | warn     |

The "no provider in noun" rule (warn) catches the common foot-gun of
embedding the source identity in the model name; the ODS contract
already captures source identity.

### Column names

Per `docs/naming-conventions.md`:

| Pattern                       | Required for                                   |
|-------------------------------|------------------------------------------------|
| `<entity>_sk`                 | every surrogate PK                             |
| `<event>_ts_utc`              | every UTC timestamp column                     |
| `<event>_date`                | every date column                              |
| `<dim>_sk`                    | every FK to a conformed dim                    |
| `_ingest_ts_utc`              | every ODS row                                  |
| `_source_id`                  | every ODS row                                  |
| `_load_batch`                 | every ODS row                                  |
| `<noun>_amt_<ccy>`            | every monetary column (currency in suffix)     |
| `<noun>_pct` or `<noun>_rate` | every percentage column                        |
| `is_<adj>` / `has_<noun>`     | every boolean column                           |

A column that looks numeric but lacks a unit suffix (`_amt_usd`,
`_pct`, `_count`) is flagged warn — the type is documented at the
schema level, but the suffix carries semantics into downstream BI.

### File and directory placement

```
models/<layer>/<model_name>.sql
models/<layer>/schema.yml
tests/<test_name>.sql        # singular tests only
seeds/<csv_or_parquet>/
```

Drift here (e.g., a DWS model living under `models/ods/`) is an error.

## Workflow

### Step 1 — Read `mart.yml`

Pull `mart_name`, `mart_prefix` (defaults to the first three characters
of `mart_name`), and `dims_are_conformed: true|false`.

### Step 2 — Scan models/

For each `.sql` file:

1. Match filename against the layer / prefix rules above.
2. Parse the SELECT list (best-effort regex; surface ambiguous SELECTs
   as `pending` rather than guessing).
3. Match every column alias against the column patterns.

### Step 3 — Cross-reference schema.yml

`schema.yml` columns must be the same set as the SQL columns. A
column documented in `schema.yml` but missing from the SQL (or vice
versa) is `error`.

### Step 4 — Emit report

Three sections in the lint report:

- **Errors** — must be fixed before merge.
- **Warnings** — review per case; downgrading to `not_applicable` is
  allowed but must be justified in the schema.yml `description:`.
- **Pending** — the linter could not statically decide; needs human
  triage.

Exit code 1 on any error-severity finding.

## Calling pattern

```sh
python scripts/lint_naming_conventions.py models/
```

In CI, this is wired alongside the existing
`scripts/lint_layer_direction.py` — the two together catch most
"someone bypassed the lifecycle and hand-edited models" drift.

## Output format

- Three lists (errors, warnings, pending) printed to stdout, each row
  named with file path + rule.
- Exit code 1 on any error.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: naming-conventions-lint`, output_artifact = path to
  the saved report or to `models/`).

## NOT for

- Cross-mart conformed-dim policy (separate skill, not in v3).
- SQL formatting (use `sqlfluff`, not this skill).
- Renames executed via `schema-evolve` — that skill already enforces
  the rule on the new column.
- Grain rules (use `grain-rules-check`).
