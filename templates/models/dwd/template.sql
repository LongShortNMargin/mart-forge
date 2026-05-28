-- {{ prefix }}_dwd_{{ entity }}_{{ grain }}
-- DWD layer: cleaned facts with business keys; joined to dimensions.
-- Grain: <one row per fact>

{{ config(materialized='table') }}

with raw as (
    select * from {{ ref('<prefix>_ods_<source>_<entity>') }}
),

joined as (
    select
        r.<business_key>,
        r.<measure_1>,
        r.<measure_2>,
        d.<entity>_sk,
        d.<entity>_attribute,
        r.provider,
        r.pull_ts_utc,
        r.run_id
    from raw r
    left join {{ ref('dim_<entity>') }} d
        on r.<business_key> = d.<entity>_id
),

derived as (
    select
        *,
        -- Derived columns: explicit SQL only. No prose.
        -- Example: <measure_1> * <measure_2> as <derived_column>
        null as placeholder_derived_column
    from joined
)

select * from derived
