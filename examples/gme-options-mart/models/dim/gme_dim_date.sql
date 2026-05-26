{{
    config(
        materialized='table'
    )
}}

SELECT
    date_key,
    full_date,
    year,
    quarter,
    month,
    month_name,
    day_of_week,
    day_name,
    is_weekend,
    CASE
        WHEN is_weekend = 1 THEN FALSE
        ELSE TRUE
    END AS is_trading_day
FROM {{ ref('dim_date') }}
