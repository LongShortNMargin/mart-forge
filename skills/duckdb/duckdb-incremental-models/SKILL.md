---
name: duckdb-incremental-models
description: "Author DuckDB incremental dbt models with unique_key, partition strategy, and a backfill protocol that doesn't blow the cloud cost ceiling — for ODS and DWD layers in any mart-forge warehouse"
user-invocable: true
---

# duckdb-incremental-models — Incremental Models on DuckDB

## When to use

Reach for this skill when a model in ODS or DWD reaches a row count
where a daily `dbt run --full-refresh` becomes too slow or too costly
(typical thresholds: >10M rows for local DuckDB, >100M rows for
MotherDuck). The skill covers `incremental` materialization patterns,
`unique_key` selection, partition pruning, and a deterministic backfill
protocol.

It is not a general "make my model fast" skill. Materialize as `table`
until measured cost or measured latency forces incremental.

## Prerequisites

- The model already runs cleanly as a `table`.
- The upstream source carries an unambiguous monotonic column
  (`event_ts`, `load_dt`, or a surrogate `batch_id`).
- The TDD §T-9 contract names `unique_key` and `incremental_strategy`
  for this model.

## Workflow

### Step 1 — Pick `unique_key`

The `unique_key` must be:

- **Stable**: the same logical row always carries the same key, even
  across reprocessing.
- **Non-null** for every emitted row.
- **Indexable** in DuckDB (single column preferred; composite keys
  work but slow merge).

Common patterns:

| Source shape                  | unique_key                                          |
|-------------------------------|-----------------------------------------------------|
| Event stream (Kafka, etc.)    | `event_id`                                          |
| Daily snapshot of dim table   | `(natural_key, snapshot_dt)` composite              |
| Append-only audit log         | composite of `source_id + _ingest_ts_utc`           |
| API pull, no real id          | hash of `(_source_id, _load_batch)`; document why   |

If no stable key exists, this is a model design bug — do not invent a
synthetic id at the dbt layer. Push back to TDD §T-9.

### Step 2 — Pick `incremental_strategy`

DuckDB supports three:

| strategy        | semantics                                   | when to use                                |
|-----------------|---------------------------------------------|--------------------------------------------|
| `append`        | New rows only; no dedupe.                   | Append-only event streams.                 |
| `delete+insert` | Delete rows in window, then insert.         | Daily windows with late-arriving updates.  |
| `merge`         | Upsert by `unique_key`.                     | SCD-2 dims, slowly-changing fact rows.     |

Default to `delete+insert` for DWD facts; default to `merge` for ODS
dim snapshots. `append` is only safe when the source guarantees no
duplicates downstream (rare).

### Step 3 — Author the model

```sql
-- models/dwd/dwd_<grain>_<entity>.sql
{{ config(
    materialized='incremental',
    unique_key='event_id',
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns',
    incremental_predicates=["DBT_INTERNAL_DEST._partition_dt >= dateadd('day', -7, current_date)"]
) }}

SELECT
    src.event_id,
    src.event_ts,
    date_trunc('day', src.event_ts)::date AS _partition_dt,
    src.payload,
    src._ingest_ts_utc,
    src._source_id,
    src._load_batch
FROM {{ ref('ods_<source>_<entity>') }} AS src
{% if is_incremental() %}
WHERE src.event_ts >= (SELECT COALESCE(MAX(event_ts), '1970-01-01'::timestamp) - INTERVAL 1 DAY FROM {{ this }})
{% endif %}
```

The `incremental_predicates` keeps DuckDB from rewriting the full table
on each `delete+insert` cycle. The 7-day window is the late-arriving
buffer — tune it to the source's actual arrival distribution.

### Step 4 — Backfill protocol

Backfill is a separate, named operation:

```sh
# Restart the model from scratch within a bounded window.
dbt run --models <model_name> \
  --vars '{backfill_window: "2026-04-01,2026-06-01"}' \
  --full-refresh
```

The model reads `var('backfill_window', null)` and, when set, replaces
its incremental WHERE clause with a window literal. This makes
backfills deterministic and reviewable — never bypass the predicate by
hand.

### Step 5 — DQC for incremental models

`8-control-dqc-audit`'s class C-3 (`uniqueness`) MUST be wired against
the `unique_key`. Class C-6 (`recency`) MUST assert that the max
`event_ts` is within the freshness SLA from TDD §T-13. Skipping either
check is what turns a quiet bug into a quarterly incident.

## Failure modes

- **Schema drift on new column** — `on_schema_change: append_new_columns`
  handles additions; deletions require a manual TDD update + full
  refresh.
- **Late data beyond the 7-day buffer** — predicate misses it. Document
  the buffer in TDD §T-13 and alarm on freshness in DQC C-6.
- **Source dedupe assumption violated** — the `append` strategy will
  silently double-count. Switch to `merge` and accept the cost.

## Output format

- One incremental dbt model with config block declaring
  `unique_key`, `incremental_strategy`, and `incremental_predicates`.
- A schema.yml entry pairing the model with at least a `unique` test
  on the declared key.
- An entry appended to `.skill-invocations.jsonl`
  (`skill_name: duckdb-incremental-models`, output_artifact = the
  new `.sql` model path).

## NOT for

- Snapshot tables (use dbt snapshots, not this skill).
- SCD-2 history (DWD-layer skill, not covered here).
- Cross-warehouse incremental joins.
- Initial DuckDB scaffold (use `creating-duckdb-mart`).
- Non-DuckDB warehouses.
