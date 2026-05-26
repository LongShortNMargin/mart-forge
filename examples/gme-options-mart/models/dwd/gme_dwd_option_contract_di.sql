{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key=['pull_date', 'option_symbol']
    )
}}

{% set rfr = var('risk_free_rate', 0.043) %}

WITH ods AS (

    SELECT *
    FROM {{ ref('gme_ods_cboe_options_chain') }}
    WHERE open_interest > 0
      AND strike IS NOT NULL

    {% if is_incremental() %}
      AND pull_date >= (SELECT COALESCE(MAX(pull_date), DATE '1900-01-01') FROM {{ this }})
    {% endif %}

),

enriched AS (

    SELECT
        ods.pull_date,
        ods.ticker,
        ods.option_symbol,
        ods.expiry,
        ods.strike,
        ods.option_type,
        ods.underlying_close AS spot,

        ods.bid,
        ods.ask,
        CASE WHEN ods.bid > 0 AND ods.ask > 0
             THEN (ods.bid + ods.ask) / 2.0
             ELSE ods.last_trade_price
        END AS mid_price,
        ods.last_trade_price,

        COALESCE(ods.volume, 0) AS volume,
        COALESCE(ods.open_interest, 0) AS open_interest,

        ods.iv AS implied_vol,

        DATE_DIFF('day', ods.pull_date, ods.expiry) AS dte,
        CAST(DATE_DIFF('day', ods.pull_date, ods.expiry) AS DOUBLE) / 365.0 AS dte_annual_frac,

        CASE
            WHEN DATE_DIFF('day', ods.pull_date, ods.expiry) > 365 THEN 'LEAP'
            WHEN DATE_DIFF('day', ods.pull_date, ods.expiry) <= 7  THEN 'WEEKLY'
            ELSE 'MONTHLY'
        END AS series_type,

        ods.provider,
        ods.pull_ts_utc,
        ods.quote_ts_utc,
        ods.run_id

    FROM ods

),

with_greeks AS (

    SELECT
        e.*,

        CASE WHEN e.dte > 0 AND e.implied_vol > 0 AND e.spot > 0 THEN
            (LN(e.spot / e.strike) + ({{ rfr }} + 0.5 * e.implied_vol * e.implied_vol) * e.dte_annual_frac)
            / (e.implied_vol * SQRT(e.dte_annual_frac))
        END AS d1,

        CASE WHEN e.dte > 0 AND e.implied_vol > 0 AND e.spot > 0 THEN
            EXP(-0.5 * POWER(
                (LN(e.spot / e.strike) + ({{ rfr }} + 0.5 * e.implied_vol * e.implied_vol) * e.dte_annual_frac)
                / (e.implied_vol * SQRT(e.dte_annual_frac))
            , 2))
            / (SQRT(2.0 * PI()) * e.spot * e.implied_vol * SQRT(e.dte_annual_frac))
        END AS bs_gamma

    FROM enriched e

)

SELECT
    g.pull_date,
    g.ticker,
    g.option_symbol,
    g.expiry,
    g.strike,
    g.option_type,
    g.spot,
    g.bid,
    g.ask,
    g.mid_price,
    g.last_trade_price,
    g.volume,
    g.open_interest,
    g.implied_vol,
    g.dte,
    g.dte_annual_frac,
    g.d1,
    g.bs_gamma,

    COALESCE(g.bs_gamma, 0)
        * g.open_interest
        * 100
        * POWER(g.spot, 2)
        * 0.01
        * CASE WHEN g.option_type = 'call' THEN 1 ELSE -1 END
    AS gex_contribution,

    g.series_type,
    g.provider,
    g.pull_ts_utc,
    g.quote_ts_utc,
    g.run_id

FROM with_greeks g
