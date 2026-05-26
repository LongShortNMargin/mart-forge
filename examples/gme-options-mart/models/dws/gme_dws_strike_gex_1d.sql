{{
    config(
        materialized='table'
    )
}}

SELECT
    pull_date,
    ticker,
    strike,
    expiry,
    dte,
    series_type,

    SUM(CASE WHEN option_type = 'call' THEN gex_contribution ELSE 0 END) AS call_gex,
    SUM(CASE WHEN option_type = 'put'  THEN gex_contribution ELSE 0 END) AS put_gex,
    SUM(gex_contribution) AS net_gex,

    SUM(open_interest) AS total_oi,
    AVG(implied_vol) AS avg_iv,

    ROW_NUMBER() OVER (
        PARTITION BY pull_date, ticker
        ORDER BY ABS(SUM(gex_contribution)) DESC
    ) AS gex_rank

FROM {{ ref('gme_dwd_option_contract_di') }}
GROUP BY pull_date, ticker, strike, expiry, dte, series_type
