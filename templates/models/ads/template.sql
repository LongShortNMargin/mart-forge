{{
  config(
    materialized='table'
  )
}}

{#
  ADS Model — Executive Dashboard OBT
  Grain: one row per calendar date.
  Metric traceability: daily_revenue -> BRD M-1 (Revenue), order_count -> BRD M-2 (Order Count).
#}

with summary_data as (
    select
        date_key,
        order_count,
        daily_revenue,
        calculated_at
    from {{ ref('{prefix}_dws_daily_revenue_1d') }}
),

date_dim as (
    select
        date_sk,
        calendar_date,
        day_name,
        is_business_day
    from {{ ref('{prefix}_dim_date') }}
)

select
    dt.calendar_date,
    dt.day_name,
    dt.is_business_day,
    s.order_count,
    s.daily_revenue,
    s.calculated_at
from summary_data s
inner join date_dim dt on s.date_key = dt.date_sk
