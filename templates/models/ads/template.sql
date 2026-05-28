-- {{ prefix }}_ads_{{ use_case }}
-- ADS layer: application-facing one-big-table for the dashboard.
-- Includes link-status columns so the dashboard can render badges.

{{ config(materialized='table') }}

with snapshot as (
    select * from {{ ref('<prefix>_dws_perf_<entity>') }}
),

joined as (
    select
        s.*,
        c.row_count                              as upstream_row_count,
        -- Per-metric link_status, sourced from coverage_manifest.json or a
        -- static mapping table. The dashboard reads these columns to
        -- render the status badge inline with each metric value.
        'verified'                               as <metric_1>_status,
        'verified'                               as <metric_2>_status,
        current_timestamp                        as ads_built_at
    from snapshot s
    left join {{ ref('<prefix>_dws_count_<entity>') }} c
        using (<grouping_key>)
)

select * from joined
