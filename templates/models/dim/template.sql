{{
  config(
    materialized='table'
  )
}}

{#
  DIM Model — Date Dimension (seed-backed, Type 0 immutable)
  Unknown member row: date_sk = -1, attributes = 'Unknown' / 0.
#}

with seed_data as (
    select
        date_sk,
        cast(calendar_date as date) as calendar_date,
        year,
        quarter,
        month,
        month_name,
        day_of_month,
        day_of_week,
        day_name,
        cast(is_weekend as boolean) as is_weekend,
        cast(is_business_day as boolean) as is_business_day,
        week_of_year
    from {{ ref('dim_date') }}
),

unknown_member as (
    select
        -1 as date_sk,
        cast('1900-01-01' as date) as calendar_date,
        0 as year,
        0 as quarter,
        0 as month,
        'Unknown' as month_name,
        0 as day_of_month,
        0 as day_of_week,
        'Unknown' as day_name,
        false as is_weekend,
        false as is_business_day,
        0 as week_of_year
)

select date_sk, calendar_date, year, quarter, month, month_name,
       day_of_month, day_of_week, day_name, is_weekend, is_business_day, week_of_year
from seed_data
union all
select date_sk, calendar_date, year, quarter, month, month_name,
       day_of_month, day_of_week, day_name, is_weekend, is_business_day, week_of_year
from unknown_member
