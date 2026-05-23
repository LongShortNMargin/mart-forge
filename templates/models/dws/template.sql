{{
  config(
    materialized='table'
  )
}}

{#
  DWS Model Template — Aggregations and Rollups

  Rules:
  - Full rebuild (table materialization)
  - Window suffix conventions: _1d (daily), _nd (rolling), _td (to-date), _mtd (month-to-date)
  - Every aggregation has explicit SQL in calculation column
  - Source_type: typically derived or hybrid
  - ref() from DWD fact tables

  Replace placeholders with actual aggregation logic from TDD T-9/T-10.
#}

with fact_data as (
    select * from {{ ref('prefix_dwd_grain_entity_di') }}
),

aggregated as (
    select
        -- Grain key(s) for the aggregation
        date_key,

        -- Count aggregations (T-9)
        -- count(distinct entity_id) as entity_count,

        -- Sum aggregations
        -- sum(metric_1) as total_metric_1,

        -- Performance / ratio aggregations (T-10)
        -- sum(numerator) / nullif(sum(denominator), 0) as ratio_metric,

        -- Window aggregations
        -- avg(metric_1) over (
        --     order by date_key
        --     rows between 6 preceding and current row
        -- ) as metric_1_7d_avg,

        -- Min/max
        -- min(metric_1) as min_metric_1,
        -- max(metric_1) as max_metric_1

        current_timestamp as calculated_at

    from fact_data
    group by date_key
)

select * from aggregated
