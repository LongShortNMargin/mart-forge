-- DWS Layer: Aggregated metrics at reporting grain
-- Materialization: table
--
-- TODO: Replace placeholders marked with {TODO_...}
-- TODO: Define aggregation grain and metric calculations

{{
    config(
        materialized='table'
    )
}}

WITH fact_source AS (

    SELECT *
    FROM {{ ref('{TODO_dwd_table_name}') }}
    -- e.g., ref('ecom_dwd_orders_cleaned')

),

aggregated AS (

    SELECT
        -- === Grain Columns ===
        -- TODO: Define the reporting grain (GROUP BY columns)
        -- date_sk,
        -- product_sk,

        -- === Count Metrics ===
        -- TODO: Add count-based metrics
        -- COUNT(DISTINCT order_id)     AS order_count,
        -- COUNT(DISTINCT customer_id)  AS unique_customers,

        -- === Performance Metrics ===
        -- TODO: Add sum/avg/min/max metrics
        -- SUM(amount)                  AS total_amount,
        -- AVG(amount)                  AS avg_order_value,

        -- === Window Metrics (optional) ===
        -- TODO: Add rolling/cumulative calculations
        -- SUM(SUM(amount)) OVER (
        --     PARTITION BY product_sk
        --     ORDER BY date_sk
        --     ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        -- ) AS rolling_7d_amount,

        -- === Metadata ===
        CURRENT_TIMESTAMP AS aggregated_at_utc

    FROM fact_source

    GROUP BY
        -- TODO: List all grain columns here
        -- date_sk,
        -- product_sk
        1  -- placeholder, remove after defining grain

)

SELECT * FROM aggregated
