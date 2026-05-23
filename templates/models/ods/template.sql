{{
  config(
    materialized='incremental',
    unique_key=var('ods_unique_key', ['pull_date', 'record_id']),
    incremental_strategy='delete+insert'
  )
}}

{#
  ODS Model Template — Raw Ingestion Layer

  Replace placeholders with actual source configuration from signed TDD.
  Rules:
  - No business logic transformations
  - Explicit column list (no SELECT *)
  - Provenance columns required on every row
  - Idempotent: re-running same partition produces identical output

  ODS Contract fields (from TDD T-6):
  - source: provider + endpoint
  - grain: what one row represents
  - logical_partition: column for incremental windowing
  - incremental_strategy: delete+insert (or append)
  - unique_key: deduplication composite
  - backfill: dbt run --vars '{partition_date: "YYYY-MM-DD"}'
  - restatement: re-run affected partition; delete+insert replaces it
  - provenance: provider, pull_ts_utc, quote_ts_utc, run_id
#}

with source_data as (
    select
        -- Source columns (explicit list from TDD T-5)
        -- column_1,
        -- column_2,
        -- column_3,

        -- Provenance columns (required)
        '{{ var("provider", "unknown") }}' as provider,
        current_timestamp as pull_ts_utc,
        null as quote_ts_utc,  -- Replace with source timestamp column
        '{{ var("run_id", "manual") }}' as run_id

    from {{ source('raw', 'source_table') }}

    {% if is_incremental() %}
    where {{ var('partition_column', 'pull_date') }}
        >= '{{ var("partition_date", (modules.datetime.datetime.now() - modules.datetime.timedelta(days=1)).strftime("%Y-%m-%d")) }}'
    {% endif %}
)

select * from source_data
