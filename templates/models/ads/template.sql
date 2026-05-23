{{
  config(
    materialized='table'
  )
}}

{#
  ADS Model Template — Application-Facing One Big Table (OBT)

  Rules:
  - Explicit column list (no SELECT *)
  - Metric-to-column traceability to upstream DWS/DWD
  - Table materialization
  - Consumer-specific: one ADS per dashboard/application
  - Every column traces to a TDD metric (T-11)
#}

with summary_data as (
    select
        date_key,
        calculated_at
        -- Add explicit DWS metric columns from TDD T-9/T-10
    from {{ ref('prefix_dws_dims_metric_window') }}
),

date_dim as (
    select
        date_sk,
        calendar_date,
        day_name,
        is_business_day
    from {{ ref('prefix_dim_date') }}
),

final as (
    select
        -- Date context
        dt.calendar_date,
        dt.day_name,
        dt.is_business_day,

        -- Metrics from DWS — trace each to BRD metric M-N
        -- Replace with actual columns from TDD T-11:
        -- s.total_metric,        -- BRD M-1, link_status: exact
        -- s.ratio_metric,        -- BRD M-2, link_status: proxy

        s.calculated_at

    from summary_data s
    inner join date_dim dt on s.date_key = dt.date_sk
)

select
    calendar_date,
    day_name,
    is_business_day,
    calculated_at
from final
