{{
  config(
    materialized='incremental',
    unique_key=['pull_date', 'record_id'],
    incremental_strategy='delete+insert'
  )
}}

{#
  ODS Model — Raw Ingestion Layer
  Grain: one row per record per pull_date.
  Strategy: delete+insert on pull_date partition.
  All columns explicit, provenance carried on every row.
  Idempotent: re-running same partition produces identical output.
#}

with source_data as (
    select
        record_id,
        cast(pull_date as date) as pull_date,
        cast(amount as decimal(10,2)) as amount,
        customer_id,
        customer_name,
        provider,
        cast(pull_ts_utc as timestamp) as pull_ts_utc,
        cast(quote_ts_utc as timestamp) as quote_ts_utc,
        run_id
    from {{ ref('raw_sample_data') }}
    {% if is_incremental() %}
    where cast(pull_date as date) >= cast('{{ var("partition_date", "2020-01-01") }}' as date)
    {% endif %}
)

select
    record_id,
    pull_date,
    amount,
    customer_id,
    customer_name,
    provider,
    pull_ts_utc,
    quote_ts_utc,
    run_id
from source_data
