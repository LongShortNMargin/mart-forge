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
  - source, grain, logical_partition, incremental_strategy
  - unique_key, backfill, restatement, provenance_columns
#}

with source_data as (
    select
        -- Source columns: explicit list from TDD T-5 (replace with actual columns)
        cast(null as varchar) as record_id,
        cast(null as date) as pull_date,

        -- Provenance columns (required on every ODS row)
        '{{ var("provider", "unknown") }}' as provider,
        current_timestamp as pull_ts_utc,
        cast(null as timestamp) as quote_ts_utc,
        '{{ var("run_id", "manual") }}' as run_id

    from {{ source('raw', 'source_table') }}

    {% if is_incremental() %}
    where {{ var('partition_column', 'pull_date') }}
        >= '{{ var("partition_date", (modules.datetime.datetime.now() - modules.datetime.timedelta(days=1)).strftime("%Y-%m-%d")) }}'
    {% endif %}
)

select
    record_id,
    pull_date,
    provider,
    pull_ts_utc,
    quote_ts_utc,
    run_id
from source_data
