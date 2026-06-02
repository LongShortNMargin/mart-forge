{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key=['trading_date', 'expiry_date', 'strike', 'option_type']) }}

with src as (
    select
        trading_date,
        expiry_date,
        cast(strike as double)             as strike,
        option_type,
        cast(open_interest as bigint)      as open_interest,
        cast(implied_volatility as double) as implied_volatility,
        provider,
        cast(pull_ts_utc as timestamp)     as pull_ts_utc,
        'run_seed'                          as run_id
    from {{ ref('gme_seed_options_chain_snapshot') }}
)

select * from src
{% if is_incremental() %}
where trading_date > (select coalesce(max(trading_date), date '1900-01-01') from {{ this }})
{% endif %}
