-- gme_dwd_options_chain — cleaned/validated options chain with front_expiry_flag.
-- front_expiry_flag = nearest expiry STRICTLY AFTER trading_date (closes Phase B.5
-- finding 4 — single source of truth for "front" used by dealer_net_gamma,
-- gex_zero_cross_strike, and max_pain_strike_front). Two-CTE form because DuckDB
-- does not allow FILTER inside window functions.

with cleaned as (
    select
        trading_date,
        expiry_date,
        strike,
        option_type,
        coalesce(open_interest, 0) as open_interest,
        case when implied_volatility > 1e-4 then implied_volatility else null end as implied_volatility,
        (expiry_date - trading_date) / 365.0 as time_to_expiry_years,
        cast(strftime(trading_date, '%Y%m%d') as integer) as date_sk,
        cast(strftime(expiry_date, '%Y%m%d') as integer)  as expiry_date_sk,
        provider,
        pull_ts_utc,
        run_id
    from {{ ref('gme_ods_options_chain_snapshot') }}
    where open_interest is not null
      and open_interest >= 0
      and option_type in ('call', 'put')
),

unexpired as (
    select distinct trading_date, expiry_date
    from cleaned
    where expiry_date > trading_date
),

front as (
    select trading_date, min(expiry_date) as front_expiry_date
    from unexpired
    group by 1
)

select
    c.trading_date,
    c.expiry_date,
    c.strike,
    c.option_type,
    c.open_interest,
    c.implied_volatility,
    c.time_to_expiry_years,
    c.date_sk,
    c.expiry_date_sk,
    (c.expiry_date = f.front_expiry_date and c.expiry_date > c.trading_date) as front_expiry_flag,
    c.provider,
    c.pull_ts_utc,
    c.run_id
from cleaned c
left join front f using (trading_date)
