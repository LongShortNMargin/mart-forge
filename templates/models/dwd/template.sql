{{
  config(
    materialized='incremental',
    unique_key='order_line_sk',
    incremental_strategy='delete+insert'
  )
}}

{#
  DWD Model — Cleaned Facts with Business Keys
  Grain: one row per order line per pull_date.
  Dedup: record_id + pull_date, latest pull_ts_utc wins.
  Native metric: amount (pass-through from ODS, source_type: native).
  Surrogate key: md5 hash (no external package dependency).
#}

with ods_source as (
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
    from {{ ref('{prefix}_ods_csv_sample') }}
    {% if is_incremental() %}
    where pull_date >= cast('{{ var("partition_date", "2020-01-01") }}' as date)
    {% endif %}
),

deduped as (
    select
        record_id,
        pull_date,
        amount,
        customer_id,
        customer_name,
        provider,
        pull_ts_utc,
        quote_ts_utc,
        run_id,
        row_number() over (
            partition by record_id, pull_date
            order by pull_ts_utc desc
        ) as _dedup_rank
    from ods_source
),

with_keys as (
    select
        md5(cast(s.record_id as varchar) || '|' || cast(s.pull_date as varchar)) as order_line_sk,
        coalesce(d.date_sk, -1) as date_key,
        s.record_id,
        s.customer_id,
        s.customer_name,
        s.amount,
        s.provider,
        s.pull_ts_utc,
        s.quote_ts_utc,
        s.run_id
    from deduped s
    left join {{ ref('{prefix}_dim_date') }} d
        on s.pull_date = d.calendar_date
    where s._dedup_rank = 1
)

select
    order_line_sk,
    date_key,
    record_id,
    customer_id,
    customer_name,
    amount,
    provider,
    pull_ts_utc,
    quote_ts_utc,
    run_id
from with_keys
