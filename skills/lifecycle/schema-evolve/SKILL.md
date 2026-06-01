---
name: schema-evolve
description: "Handle source schema changes for a Kimball mart — adds new columns to ODS, propagates business attributes to DWD, adds appropriate tests, and updates schema.yml documentation"
user-invocable: true
---

# schema-evolve — Additive schema migration

## When to use

Invoke this skill when an upstream data provider has added a new column
(or renamed one) and you need to propagate the change through the
warehouse without rebuilding from scratch.

This skill handles **additive** changes only. Removals, type changes
to existing columns, and grain changes require manual review and
typically a fresh TDD signing pass.

## Prerequisites

- A built scaffold (`mart.yml` shows `phase: C_complete` or later).
- A signed TDD on file.
- The new column's name, type, and business definition.
- The provider field that maps to it (for native) or the derivation SQL
  (for derived).

## Hard gate

```
GATE: This skill is additive only. Removals and type changes need a fresh TDD pass.
```

If the proposed change includes a removal, a type change to an existing
column, or a change of grain, reject:

```
BLOCKED: Non-additive change detected.
  - removed columns: [...]
  - type-changed columns: [...]
  - grain change: <yes/no>
Open a fresh TDD via /mart-tdd.
```

## Workflow

### Step 1 — Confirm additivity

Compare the new schema against the current TDD §T-8 column catalog.
Classify every change as:
- **Added** column (proceed).
- **Renamed** column (treat as added + remove the old; route to fresh
  TDD).
- **Removed** column (reject).
- **Type changed** (reject).

### Step 2 — Update the TDD

Add the new column to:
- §T-8 master column catalog with all 6 fields.
- §T-9 ODS table (if native) or §T-11/T-12/T-13 (if derived).
- §T-18 DQC plan with the appropriate control class.
- §T-19 test case if the column needs a specific test.

Bump the version in T-1 changelog with a short note ("Added column X
from provider Y").

### Step 3 — Update the ODS model

If native: add the column to the ODS SELECT list with the provider
field mapping.

If the source is a parquet/CSV drop, confirm the new field exists in
the latest pull.

### Step 4 — Propagate to DWD (if applicable)

If the column carries business meaning that downstream models need, add
it to the DWD model with the appropriate JOIN and any derivation.

### Step 5 — Add tests

For the new column, add the tests implied by its source_type:
- `native` numeric → not_null + range check (if known bounds).
- `derived` numeric → not_null + formula validation + accepted_range.
- All columns → null-rate threshold per `dqc-framework.md`.

### Step 6 — Update schema.yml

Document the column with a `description`, expected `data_type`, and
the tests added.

### Step 7 — Run a smoke build

```
dbt run --select +<modified_dwd_model>+
dbt test --select +<modified_dwd_model>+
```

If anything fails, report and roll back the in-memory edits — DO NOT
commit a broken state.

### Step 8 — Update dashboard (if surfaced)

If the new column is meant to render on the dashboard, add the rendering
hook in `dashboard/app.py` with the status badge.

### Step 9 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "schema-evolve", "input_artifact": "<column spec>", "output_artifact": "<list of edited files>", "checkpoint": "schema_evolve", "reconstructed": false}
```

### Step 10 — Print migration notes

A summary of what changed, what was added, and what the reviewer
should focus on.

## Output format

Edits to TDD, ODS model, DWD model (if applicable), schema.yml,
dashboard (if applicable). Migration notes printed to session.

## NOT for

- Removing or renaming columns (treat as a fresh TDD pass).
- Changing grain (architectural — requires fresh TDD).
- Adding entire new source tables (use `/mart-bootstrap` for the new
  entity).
- Fixing broken tests (investigate root cause; do not paper over with a
  schema change).
