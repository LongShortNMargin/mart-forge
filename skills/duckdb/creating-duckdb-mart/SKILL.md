---
name: creating-duckdb-mart
description: "Stand up a DuckDB-backed Kimball mart with parquet seeds, an incremental staging contract, and an optional MotherDuck deploy target — for any new analytics warehouse on local + cloud DuckDB"
user-invocable: true
---

# creating-duckdb-mart — DuckDB / MotherDuck Mart Scaffold

## When to use

Invoke this skill when the signed TDD calls for a DuckDB warehouse —
either a local single-file mart, a parquet-on-S3 lakehouse, or a cloud
mart hosted on MotherDuck. The lifecycle skills (`mart-bootstrap`,
`mart-dqc`) cover scaffolding shape; this skill specializes the dbt
profile, materialization defaults, and seed strategy to DuckDB.

Reach for this skill instead of a generic dbt scaffold when:

- The TDD §T-9 ODS contract names DuckDB as the platform.
- You want parquet seeds (fast cold-start, deterministic fixtures).
- A future MotherDuck deploy is in scope; the deploy is staged behind
  a profile target, not a code rewrite.

## Prerequisites

- Signed TDD (CI-enforced by `scripts/lint_signed_tdd.py`).
- `mart.yml` with `mart_name`, `platform: duckdb`, optional `motherduck_database`.
- Local toolchain: `duckdb >= 0.10`, `dbt-duckdb >= 1.7`, `python >= 3.11`.

## Workflow

### Step 1 — Lay down the profile

Write `profiles/<mart_name>.yml` with two targets:

```yaml
<mart_name>:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: ./warehouse/<mart_name>.duckdb
      schema: main
      threads: 4
    prod:
      type: duckdb
      path: "md:<motherduck_database>"  # MotherDuck cloud
      schema: main
      threads: 4
      extensions: [httpfs]
```

The `dev` target keeps the entire warehouse in a single file inside
the worktree. The `prod` target writes to MotherDuck via the `md:`
URI scheme. Real credentials live in the operator's environment, not
the profile (see `motherduck-deploy`).

### Step 2 — Seed strategy

For deterministic fixtures, store seeds as parquet under
`seeds/parquet/` and load them with `read_parquet()` macros instead of
dbt's row-by-row CSV import. CSV is reserved for dim_date and small
controlled-vocabulary tables.

```sql
-- macros/load_parquet_seed.sql
{% macro load_parquet_seed(name) %}
  SELECT * FROM read_parquet('{{ project_path('seeds/parquet/' ~ name ~ '.parquet') }}')
{% endmacro %}
```

### Step 3 — Materialization defaults

In `dbt_project.yml`:

```yaml
models:
  <mart_name>:
    ods:   {+materialized: incremental, +on_schema_change: append_new_columns}
    dim:   {+materialized: table}
    dwd:   {+materialized: incremental}
    dws:   {+materialized: table}
    ads:   {+materialized: view}
```

The choice of `incremental` for ODS and DWD lets day-over-day
production runs stay under the cloud-cost ceiling declared in TDD §T-14.

### Step 4 — Provenance columns

Every ODS model selects three provenance columns the DWD layer carries
forward and the DQC layer audits:

| column            | source                              | dtype     |
|-------------------|-------------------------------------|-----------|
| `_ingest_ts_utc`  | `now()` at the moment of write      | timestamp |
| `_source_id`      | source-system row identifier        | varchar   |
| `_load_batch`     | logical batch / partition tag       | varchar   |

DQC's class C-7 (`provenance_completeness`) reads these columns. If you
skip them, the audit will fail later — bake them in here.

### Step 5 — Smoke the warehouse

```sh
dbt deps
dbt seed --target dev
dbt build --target dev
duckdb ./warehouse/<mart_name>.duckdb -c "SELECT COUNT(*) FROM main.dim_date"
```

A non-zero row count on `dim_date` is the cheapest signal the profile
is wired up.

## Output format

- `dbt_project.yml` with the per-layer materialization defaults.
- `profiles/<mart_name>.yml` with `dev` + `prod` (MotherDuck) targets.
- `macros/load_parquet_seed.sql` macro.
- A green `dbt build` on the dev target.
- An entry appended to `.skill-invocations.jsonl` recording the
  invocation (`skill_name: creating-duckdb-mart`, output_artifact =
  the path of the new `dbt_project.yml`).

## NOT for

- MotherDuck token management → `motherduck-deploy`.
- DQC catalog wiring → `mart-dqc` + `8-control-dqc-audit`.
- Long-running cost optimization → not in v3.
- Snowflake / BigQuery / Postgres mart bootstrap (this is the DuckDB
  track; the lifecycle skills cover the warehouse-agnostic layer).
