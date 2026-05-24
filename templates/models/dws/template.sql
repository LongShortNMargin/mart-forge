{{
  config(
    materialized='table'
  )
}}

{#
  DWS Model — Daily Revenue Aggregation (1d window)
  Grain: one row per date_key.
  Metrics: order_count (COUNT, derived), daily_revenue (SUM, derived).
#}

with fact_data as (
    select
        date_key,
        amount,
        record_id
    from {{ ref('{prefix}_dwd_daily_sample_di') }}
)

select
    date_key,
    count(distinct record_id) as order_count,
    cast(sum(amount) as decimal(12,2)) as daily_revenue,
    current_timestamp as calculated_at
from fact_data
group by date_key
