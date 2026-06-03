{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key=['trading_date', 'expiry_date', 'strike', 'option_type']) }}

-- Synthetic seed + isolated test fixtures (TC-16 max_pain @ 2099-12-31,
-- TC-17 iv_rank @ 2098-01-01..2099-02-04). Fixture trading_dates are well
-- outside the dim_date 2020-2027 coverage of real yfinance pulls, so steady-state
-- queries against current dates never touch them.

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

    union all

    select
        trading_date,
        expiry_date,
        cast(strike as double)             as strike,
        option_type,
        cast(open_interest as bigint)      as open_interest,
        cast(implied_volatility as double) as implied_volatility,
        provider,
        cast(pull_ts_utc as timestamp)     as pull_ts_utc,
        'run_fixture_tc16'                  as run_id
    from {{ ref('max_pain_asymmetric_chain') }}

    union all

    select
        trading_date,
        expiry_date,
        cast(strike as double)             as strike,
        option_type,
        cast(open_interest as bigint)      as open_interest,
        cast(implied_volatility as double) as implied_volatility,
        provider,
        cast(pull_ts_utc as timestamp)     as pull_ts_utc,
        'run_fixture_tc17'                  as run_id
    from {{ ref('iv_rank_synthetic_400d_chain') }}
)

select * from src
{% if is_incremental() %}
where trading_date > (select coalesce(max(trading_date), date '1900-01-01') from {{ this }})
{% endif %}
