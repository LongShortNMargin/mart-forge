-- gme_ads_market_dashboard — single-row presentation view for the Streamlit dashboard.
-- Materialised as a VIEW (closes Phase B.5 finding 3): most_recent_session_close_ts_utc,
-- pull_lag_hours, and is_stale re-evaluate at every dashboard query so STALE fires on
-- Monday-morning queries against an unrefreshed Friday materialisation.
--
-- most_recent_session_close_ts_utc uses the "most recent close in the past" form
-- (closes Phase B.5 finding B): MAX(calendar_date + 21h) WHERE calendar_date + 21h <= now().
-- This keeps pull_lag_hours in [0, ∞) — STALE fires once next-session-close passes
-- without a fresh pull, instead of returning negative lag values pre-21:00 UTC.

with latest_date as (
    select max(p.trading_date) as trading_date
    from {{ ref('gme_dwd_price_eod') }} p
    inner join (select distinct trading_date from {{ ref('gme_dwd_options_chain') }}) c
        on p.trading_date = c.trading_date
),

pc_ratio as (
    select
        trading_date,
        sum(case when option_type = 'put'  then open_interest else 0 end) * 1.0
          / nullif(sum(case when option_type = 'call' then open_interest else 0 end), 0)
            as pc_ratio_oi
    from {{ ref('gme_dwd_options_chain') }}
    group by 1
),

ods_pull_chain as (
    select trading_date, max(pull_ts_utc) as pull_ts_chain
    from {{ ref('gme_ods_options_chain_snapshot') }}
    group by 1
),

ods_pull_price as (
    select trading_date, max(pull_ts_utc) as pull_ts_price
    from {{ ref('gme_ods_price_history') }}
    group by 1
),

mp_front as (
    select
        mp.trading_date,
        mp.max_pain_strike as max_pain_strike_front
    from {{ ref('gme_dws_perf_max_pain') }} mp
    inner join (
        select distinct trading_date, expiry_date
        from {{ ref('gme_dwd_options_chain_greeks') }}
        where front_expiry_flag = true
    ) fe
      on fe.trading_date = mp.trading_date
     and fe.expiry_date  = mp.expiry_date
),

freshness as (
    select
        (select max(calendar_date + interval '21 hours')
         from {{ ref('dim_date') }}
         where is_trading_day = true
           and calendar_date + interval '21 hours' <= now()
        ) as most_recent_session_close_ts_utc
)

select
    l.trading_date,
    (select close_px from {{ ref('gme_dwd_price_eod') }} where trading_date = l.trading_date) as spot,
    (select max_pain_strike_front from mp_front where trading_date = l.trading_date)          as max_pain_strike_front,
    (select pc_ratio_oi from pc_ratio where trading_date = l.trading_date)                    as pc_ratio_oi,
    (select iv30 from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) as iv30,
    (select hv20 from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) as hv20,
    (select net_gex from {{ ref('gme_dws_perf_dealer_gamma') }} where trading_date = l.trading_date) as net_gex,
    (select gex_zero_cross_strike from {{ ref('gme_dws_perf_dealer_gamma_front_month') }} where trading_date = l.trading_date) as gex_zero_cross_strike,
    (select dealer_net_gamma from {{ ref('gme_dws_perf_dealer_gamma_front_month') }} where trading_date = l.trading_date) as dealer_net_gamma,
    (select iv_rank from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) as iv_rank,
    (select iv_rank_label from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) as iv_rank_label,
    (select iv_rank_lookback_days from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) as iv_rank_lookback_days,
    case
        when (select iv_rank_lookback_days from {{ ref('gme_dws_perf_implied_vol') }} where trading_date = l.trading_date) >= 252
            then 'proxy'
        else 'unsupported'
    end as iv_rank_link_status_active,
    greatest(
        coalesce((select pull_ts_chain from ods_pull_chain where trading_date = l.trading_date), cast('1900-01-01' as timestamp)),
        coalesce((select pull_ts_price from ods_pull_price where trading_date = l.trading_date), cast('1900-01-01' as timestamp))
    ) as last_pull_ts_utc,
    f.most_recent_session_close_ts_utc,
    extract(epoch from (
        greatest(
            coalesce((select pull_ts_chain from ods_pull_chain where trading_date = l.trading_date), cast('1900-01-01' as timestamp)),
            coalesce((select pull_ts_price from ods_pull_price where trading_date = l.trading_date), cast('1900-01-01' as timestamp))
        ) - f.most_recent_session_close_ts_utc
    )) / 3600.0 as pull_lag_hours,
    not (
        extract(epoch from (
            greatest(
                coalesce((select pull_ts_chain from ods_pull_chain where trading_date = l.trading_date), cast('1900-01-01' as timestamp)),
                coalesce((select pull_ts_price from ods_pull_price where trading_date = l.trading_date), cast('1900-01-01' as timestamp))
            ) - f.most_recent_session_close_ts_utc
        )) / 3600.0 >= 0
        and extract(epoch from (
            greatest(
                coalesce((select pull_ts_chain from ods_pull_chain where trading_date = l.trading_date), cast('1900-01-01' as timestamp)),
                coalesce((select pull_ts_price from ods_pull_price where trading_date = l.trading_date), cast('1900-01-01' as timestamp))
            ) - f.most_recent_session_close_ts_utc
        )) / 3600.0 <= 26
    ) as is_stale,
    cast(strftime(l.trading_date, '%Y%m%d') as integer) as date_sk
from latest_date l
cross join freshness f
