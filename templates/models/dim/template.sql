-- dim_{{ entity }}
-- DIM layer: conformed dimension. Either seed-backed or derived from ODS.
-- Grain: <one row per entity>

{{ config(materialized='table') }}

with src as (
    -- For seed-backed dimensions:
    select * from {{ ref('seed_<entity>') }}

    -- For ODS-derived dimensions, replace with:
    -- select distinct <columns> from {{ ref('<prefix>_ods_<source>_<entity>') }}
),

with_sk as (
    select
        row_number() over (order by <natural_key>) as <entity>_sk,
        <natural_key>                                as <entity>_id,
        <other_columns>
    from src
)

select * from with_sk
