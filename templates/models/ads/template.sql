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
    select * from {{ ref('prefix_dws_dims_metric_window') }}
),

dimension_data as (
    select * from {{ ref('prefix_dim_entity') }}
),

date_data as (
    select * from {{ ref('prefix_dim_date') }}
),

final as (
    select
        -- Date context
        dt.calendar_date,
        dt.day_of_week,
        dt.is_business_day,

        -- Dimension context
        dim.entity_name,

        -- Metrics from DWS (trace each to TDD)
        -- s.total_metric_1,        -- TDD metric M-1
        -- s.ratio_metric,          -- TDD metric M-2
        -- s.entity_count,          -- TDD metric M-3

        -- Calculated at timestamp
        s.calculated_at

    from summary_data s
    left join date_data dt on s.date_key = dt.date_sk
    left join dimension_data dim on s.entity_key = dim.entity_sk
)

select * from final
