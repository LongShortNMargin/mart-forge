{{
  config(
    materialized='table'
  )
}}

{#
  DWS Model Template — Aggregations and Rollups

  Rules:
  - Full rebuild (table materialization)
  - Window suffix: _1d (daily), _nd (rolling), _td (to-date), _mtd (month-to-date)
  - Every aggregation has explicit SQL in calculation column
  - Source_type: typically derived or hybrid
  - Explicit column list — no SELECT *
#}

with fact_data as (
    select
        date_key,
        -- Add explicit DWD columns from TDD T-8 needed for aggregation
        provider,
        pull_ts_utc
    from {{ ref('prefix_dwd_grain_entity_di') }}
),

aggregated as (
    select
        date_key,

        -- Count aggregations (T-9, source_type: derived)
        -- count(distinct entity_key) as entity_count,

        -- Sum aggregations (T-9, source_type: derived)
        -- sum(metric_column) as total_metric,

        -- Performance / ratio aggregations (T-10, source_type: derived)
        -- sum(numerator_col) / nullif(sum(denominator_col), 0) as ratio_metric,

        current_timestamp as calculated_at

    from fact_data
    group by date_key
)

select
    date_key,
    calculated_at
from aggregated
