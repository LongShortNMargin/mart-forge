{{
    config(
        materialized='table'
    )
}}

WITH gex_agg AS (
    SELECT
        pull_date,
        ticker,
        SUM(net_gex) AS net_gex,
        (SELECT strike FROM {{ ref('gme_dws_strike_gex_1d') }} g2
         WHERE g2.pull_date = g1.pull_date AND g2.ticker = g1.ticker
         ORDER BY ABS(g2.net_gex) DESC LIMIT 1) AS top_gex_strike
    FROM {{ ref('gme_dws_strike_gex_1d') }} g1
    GROUP BY pull_date, ticker
),

max_pain AS (
    WITH pain_calc AS (
        SELECT
            c1.pull_date,
            c1.ticker,
            c1.strike AS candidate,
            SUM(CASE
                WHEN c2.option_type = 'call' AND c2.strike < c1.strike
                THEN (c1.strike - c2.strike) * c2.open_interest * 100
                WHEN c2.option_type = 'put' AND c2.strike > c1.strike
                THEN (c2.strike - c1.strike) * c2.open_interest * 100
                ELSE 0
            END) AS total_pain
        FROM {{ ref('gme_dwd_option_contract_di') }} c1
        CROSS JOIN {{ ref('gme_dwd_option_contract_di') }} c2
        WHERE c1.pull_date = c2.pull_date AND c1.ticker = c2.ticker
        GROUP BY c1.pull_date, c1.ticker, c1.strike
    )
    SELECT pull_date, ticker, candidate AS max_pain_strike
    FROM pain_calc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY pull_date, ticker ORDER BY total_pain ASC) = 1
),

pc_ratio AS (
    SELECT
        pull_date,
        ticker,
        SUM(CASE WHEN option_type = 'put' THEN open_interest ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN option_type = 'call' THEN open_interest ELSE 0 END), 0)
            AS pc_ratio
    FROM {{ ref('gme_dwd_option_contract_di') }}
    GROUP BY pull_date, ticker
),

top_oi AS (
    SELECT
        pull_date, ticker, strike, open_interest,
        ROW_NUMBER() OVER (PARTITION BY pull_date, ticker ORDER BY open_interest DESC) AS oi_rank
    FROM (
        SELECT pull_date, ticker, strike, SUM(open_interest) AS open_interest
        FROM {{ ref('gme_dwd_option_contract_di') }}
        GROUP BY pull_date, ticker, strike
    )
),

spot AS (
    SELECT DISTINCT pull_date, ticker, spot
    FROM {{ ref('gme_dwd_option_contract_di') }}
)

SELECT
    s.pull_date,
    s.ticker,
    s.spot,

    mp.max_pain_strike,
    ROUND(ABS(s.spot - mp.max_pain_strike) / s.spot * 100, 2) AS max_pain_convergence_pct,

    ga.net_gex,
    ga.top_gex_strike,

    pc.pc_ratio,

    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 1) AS top_oi_strike_1,
    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 2) AS top_oi_strike_2,
    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 3) AS top_oi_strike_3

FROM spot s
LEFT JOIN gex_agg ga ON s.pull_date = ga.pull_date AND s.ticker = ga.ticker
LEFT JOIN max_pain mp ON s.pull_date = mp.pull_date AND s.ticker = mp.ticker
LEFT JOIN pc_ratio pc ON s.pull_date = pc.pull_date AND s.ticker = pc.ticker
