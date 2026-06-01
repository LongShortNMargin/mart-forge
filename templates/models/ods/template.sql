-- {{ prefix }}_ods_{{ source }}_{{ entity }}
-- ODS layer: pass-through ingestion with provenance columns.
-- Source: <provider + endpoint>
-- Grain: <one row per ...>
-- Incremental key: <logical partition column, e.g. pull_date>

{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key=['<logical_partition>', '<natural_key>']
) }}

with source as (
    select * from {{ source('<source>', '<asset>') }}
),

provenance as (
    select
        *,
        '<provider_name>'                as provider,
        current_timestamp                 as pull_ts_utc,
        '{{ invocation_id }}'             as run_id
    from source
)

select * from provenance

{% if is_incremental() %}
where <logical_partition> > (select coalesce(max(<logical_partition>), '1900-01-01') from {{ this }})
{% endif %}
