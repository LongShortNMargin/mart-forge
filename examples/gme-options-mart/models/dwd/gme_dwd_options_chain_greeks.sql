-- gme_dwd_options_chain_greeks — Black-Scholes γ joined with spot.
-- sign_dealer comes from dealer_assumption (BRD §B-2): -1 for calls, +1 for puts.
-- It is the SOLE source of dealer-signing for net_gex, dealer_net_gamma, and the
-- gex_zero_cross_strike per-strike GEX; no downstream re-derivation from option_type.

{% set r = var('risk_free_rate', 0.045) %}

with chain as (
    select * from {{ ref('gme_dwd_options_chain') }}
),

price as (
    select trading_date, close_px from {{ ref('gme_dwd_price_eod') }}
),

joined as (
    select
        c.trading_date,
        c.expiry_date,
        c.strike,
        c.option_type,
        c.open_interest,
        c.implied_volatility as sigma,
        p.close_px            as spot,
        c.time_to_expiry_years,
        c.front_expiry_flag,
        c.pull_ts_utc
    from chain c
    inner join price p on p.trading_date = c.trading_date
),

with_d1 as (
    select
        *,
        cast({{ r }} as double) as risk_free_rate,
        case
            when sigma is null then null
            when time_to_expiry_years <= 0 then null
            else (ln(spot / nullif(strike, 0)) + ({{ r }} + 0.5 * pow(sigma, 2)) * time_to_expiry_years)
                 / (sigma * sqrt(time_to_expiry_years))
        end as d1
    from joined
)

select
    trading_date,
    expiry_date,
    strike,
    option_type,
    open_interest,
    sigma,
    spot,
    risk_free_rate,
    time_to_expiry_years,
    case
        when d1 is null then null
        when sigma is null or sigma <= 0 then null
        when time_to_expiry_years <= 0 then null
        else exp(- pow(d1, 2) / 2.0) / (sigma * spot * sqrt(2.0 * pi() * time_to_expiry_years))
    end as gamma_bs,
    case option_type when 'call' then -1 when 'put' then 1 end as sign_dealer,
    front_expiry_flag,
    cast(strftime(trading_date, '%Y%m%d') as integer) as date_sk,
    pull_ts_utc
from with_d1
