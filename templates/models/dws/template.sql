-- {{ prefix }}_dws_{{ agg_type }}_{{ entity }}
-- DWS layer: aggregations at reporting grain.
-- Grain: <one row per aggregation key>
-- agg_type: 'count' for count-type aggregations (T-12)
--           'perf'  for performance/rate aggregations (T-13)

{{ config(materialized='table') }}

with src as (
    select * from {{ ref('<prefix>_dwd_<entity>_<grain>') }}
),

agg as (
    select
        <grouping_key_1>,
        <grouping_key_2>,
        -- COUNT-type measures (T-12):
        count(*)                            as row_count,
        count(distinct <key>)               as unique_count,
        -- PERFORMANCE-type measures (T-13):
        avg(<measure>)                      as avg_<measure>,
        sum(<measure>)                      as total_<measure>,
        percentile_cont(0.5) within group (order by <measure>) as median_<measure>
    from src
    group by <grouping_key_1>, <grouping_key_2>
)

select * from agg
