{{
    config(
        materialized='table'
    )
}}

WITH strike_gex_agg AS (
    SELECT
        pull_date, ticker, strike,
        SUM(net_gex) AS net_gex_at_strike
    FROM {{ ref('gme_dws_strike_gex_1d') }}
    GROUP BY pull_date, ticker, strike
),

cum_gex AS (
    SELECT
        pull_date, ticker, strike, net_gex_at_strike,
        SUM(net_gex_at_strike) OVER w AS cum_gex,
        LEAD(strike) OVER w AS next_strike
    FROM strike_gex_agg
    WINDOW w AS (PARTITION BY pull_date, ticker ORDER BY strike)
),

cum_gex_with_next AS (
    SELECT
        pull_date, ticker, strike, net_gex_at_strike,
        cum_gex, next_strike,
        LEAD(cum_gex) OVER (
            PARTITION BY pull_date, ticker ORDER BY strike
        ) AS next_cum_gex
    FROM cum_gex
),

gamma_flip_crossing AS (
    SELECT
        pull_date, ticker,
        strike + (0 - cum_gex)
            / NULLIF(next_cum_gex - cum_gex, 0)
            * (next_strike - strike) AS gamma_flip_point
    FROM cum_gex_with_next
    WHERE (cum_gex >= 0 AND next_cum_gex < 0)
       OR (cum_gex < 0 AND next_cum_gex >= 0)
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY pull_date, ticker ORDER BY strike
    ) = 1
),

gamma_flip_fallback AS (
    SELECT pull_date, ticker, strike AS gamma_flip_point
    FROM cum_gex
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY pull_date, ticker ORDER BY ABS(cum_gex)
    ) = 1
),

gamma_flip AS (
    SELECT
        fb.pull_date, fb.ticker,
        COALESCE(cr.gamma_flip_point, fb.gamma_flip_point) AS gamma_flip_point
    FROM gamma_flip_fallback fb
    LEFT JOIN gamma_flip_crossing cr
        ON fb.pull_date = cr.pull_date AND fb.ticker = cr.ticker
),

iv30_calc AS (
    SELECT
        pull_date, ticker,
        SUM(implied_vol * open_interest) * 1.0
            / NULLIF(SUM(open_interest), 0) AS iv30
    FROM {{ ref('gme_dwd_option_contract_di') }}
    WHERE dte BETWEEN 20 AND 40
      AND implied_vol IS NOT NULL
    GROUP BY pull_date, ticker
),

dealer_gamma AS (
    SELECT
        pull_date, ticker,
        SUM(gex_contribution) AS dealer_net_gamma
    FROM {{ ref('gme_dwd_option_contract_di') }}
    GROUP BY pull_date, ticker
),

daily_oi AS (
    SELECT
        pull_date, ticker,
        SUM(open_interest) AS total_oi
    FROM {{ ref('gme_dwd_option_contract_di') }}
    GROUP BY pull_date, ticker
),

oi_delta AS (
    SELECT
        pull_date, ticker,
        total_oi - LAG(total_oi) OVER (
            PARTITION BY ticker ORDER BY pull_date
        ) AS oi_daily_delta
    FROM daily_oi
),

underlying_returns AS (
    SELECT
        uc.trade_date,
        uc.ticker,
        uc.close_price,
        LN(uc.close_price / LAG(uc.close_price) OVER (
            PARTITION BY uc.ticker ORDER BY uc.trade_date
        )) AS log_return
    FROM {{ ref('gme_underlying_closes') }} uc
),

hv20_calc AS (
    SELECT
        trade_date,
        ticker,
        CASE
            WHEN COUNT(log_return) OVER w >= 20
            THEN STDDEV(log_return) OVER w * SQRT(252)
        END AS hv20
    FROM underlying_returns
    WINDOW w AS (
        PARTITION BY ticker
        ORDER BY trade_date
        ROWS BETWEEN 20 PRECEDING AND CURRENT ROW
    )
),

iv30_numbered AS (
    SELECT
        pull_date, ticker, iv30,
        ROW_NUMBER() OVER (
            PARTITION BY ticker ORDER BY pull_date
        ) AS session_num
    FROM iv30_calc
),

iv_history AS (
    SELECT
        i.pull_date,
        i.ticker,
        i.iv30,
        MIN(i2.iv30) AS min_iv30_252d,
        MAX(i2.iv30) AS max_iv30_252d,
        COUNT(i2.iv30) AS iv30_day_count,
        SUM(CASE WHEN i2.iv30 < i.iv30 THEN 1 ELSE 0 END) AS days_below
    FROM iv30_numbered i
    LEFT JOIN iv30_numbered i2
        ON i.ticker = i2.ticker
       AND i2.session_num BETWEEN i.session_num - 251 AND i.session_num
    GROUP BY i.pull_date, i.ticker, i.iv30
),

pull_dates AS (
    SELECT DISTINCT pull_date, ticker
    FROM {{ ref('gme_dwd_option_contract_di') }}
)

SELECT
    pd.pull_date,
    pd.ticker,

    ROUND(gf.gamma_flip_point, 2) AS gamma_flip_point,
    ROUND(iv.iv30, 4) AS iv30,
    ROUND(hv.hv20, 4) AS hv20,

    CASE
        WHEN ivh.iv30_day_count >= 20
        THEN ROUND(
            (ivh.iv30 - ivh.min_iv30_252d)
            / NULLIF(ivh.max_iv30_252d - ivh.min_iv30_252d, 0),
            4
        )
    END AS iv_rank,

    oi.oi_daily_delta,

    ROUND(dg.dealer_net_gamma, 2) AS dealer_net_gamma,

    CASE
        WHEN ivh.iv30_day_count >= 20
        THEN ROUND(
            ivh.days_below * 1.0
            / NULLIF(ivh.iv30_day_count, 0),
            4
        )
    END AS iv_percentile

FROM pull_dates pd
LEFT JOIN gamma_flip gf
    ON pd.pull_date = gf.pull_date AND pd.ticker = gf.ticker
LEFT JOIN iv30_calc iv
    ON pd.pull_date = iv.pull_date AND pd.ticker = iv.ticker
LEFT JOIN (
    SELECT trade_date, ticker, hv20
    FROM hv20_calc
    WHERE hv20 IS NOT NULL
) hv ON pd.ticker = hv.ticker
    AND hv.trade_date = (
        SELECT MAX(h2.trade_date)
        FROM hv20_calc h2
        WHERE h2.ticker = pd.ticker
          AND h2.trade_date <= pd.pull_date
          AND h2.hv20 IS NOT NULL
    )
LEFT JOIN iv_history ivh
    ON pd.pull_date = ivh.pull_date AND pd.ticker = ivh.ticker
LEFT JOIN oi_delta oi
    ON pd.pull_date = oi.pull_date AND pd.ticker = oi.ticker
LEFT JOIN dealer_gamma dg
    ON pd.pull_date = dg.pull_date AND pd.ticker = dg.ticker
