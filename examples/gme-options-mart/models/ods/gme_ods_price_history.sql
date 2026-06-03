{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='trading_date') }}

-- Synthetic seed + iv_rank fixture price history (TC-17 dates only).
-- max_pain (TC-16) does not depend on price, so no fixture price row is needed
-- at 2099-12-31.

with src as (
    select
        trading_date,
        cast(open_px as double)         as open_px,
        cast(high_px as double)         as high_px,
        cast(low_px as double)          as low_px,
        cast(close_px as double)        as close_px,
        cast(volume as bigint)          as volume,
        provider,
        cast(pull_ts_utc as timestamp)  as pull_ts_utc,
        'run_seed'                       as run_id
    from {{ ref('gme_seed_price_history') }}

    union all

    select
        trading_date,
        cast(open_px as double)         as open_px,
        cast(high_px as double)         as high_px,
        cast(low_px as double)          as low_px,
        cast(close_px as double)        as close_px,
        cast(volume as bigint)          as volume,
        provider,
        cast(pull_ts_utc as timestamp)  as pull_ts_utc,
        'run_fixture_tc17'               as run_id
    from {{ ref('iv_rank_synthetic_400d_price') }}
)

select * from src
{% if is_incremental() %}
where trading_date > (select coalesce(max(trading_date), date '1900-01-01') from {{ this }})
{% endif %}
