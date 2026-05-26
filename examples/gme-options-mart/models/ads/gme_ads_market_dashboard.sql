{{
    config(
        materialized='table'
    )
}}

WITH snapshot AS (
    SELECT pull_date, ticker, spot, max_pain_strike, max_pain_convergence_pct,
           net_gex, top_gex_strike, pc_ratio, top_oi_strike_1, top_oi_strike_2, top_oi_strike_3
    FROM {{ ref('gme_dws_daily_snapshot_1d') }}
),

metrics AS (
    SELECT pull_date, ticker, gamma_flip_point, iv30, hv20, iv_rank,
           oi_daily_delta, dealer_net_gamma, iv_percentile
    FROM {{ ref('gme_dws_options_metrics_1d') }}
),

date_dim AS (
    SELECT full_date, year, quarter, month_name, day_name, is_trading_day
    FROM {{ ref('gme_dim_date') }}
)

SELECT
    sn.pull_date,
    sn.ticker,
    sn.spot,

    d.year,
    d.quarter,
    d.month_name,
    d.day_name,
    d.is_trading_day,

    sn.max_pain_strike,
    sn.max_pain_convergence_pct,
    sn.net_gex,
    sn.top_gex_strike,
    sn.pc_ratio,
    sn.top_oi_strike_1,
    sn.top_oi_strike_2,
    sn.top_oi_strike_3,

    m.gamma_flip_point,
    m.iv30,
    m.hv20,
    m.iv_rank,
    m.oi_daily_delta,
    m.dealer_net_gamma,
    m.iv_percentile

FROM snapshot sn
LEFT JOIN metrics m
    ON sn.pull_date = m.pull_date AND sn.ticker = m.ticker
LEFT JOIN date_dim d
    ON sn.pull_date = d.full_date
