-- ADS Layer: Application-facing one-big-table for presentation
-- Materialization: table
--
-- TODO: Replace placeholders marked with {TODO_...}
-- TODO: Join DWS metrics with DIM attributes for dashboard consumption

{{
    config(
        materialized='table'
    )
}}

WITH metrics AS (

    SELECT *
    FROM {{ ref('{TODO_dws_table_name}') }}
    -- e.g., ref('ecom_dws_daily_sales')

),

-- TODO: Add additional DWS sources if combining multiple aggregations
-- metrics_2 AS (
--     SELECT * FROM {{ ref('{TODO_dws_table_name_2}') }}
-- ),

enriched AS (

    SELECT
        -- === Date Attributes ===
        -- TODO: Join dim_date for human-readable date fields
        -- dim_date.full_date,
        -- dim_date.year,
        -- dim_date.quarter,
        -- dim_date.month_name,
        -- dim_date.day_name,
        -- dim_date.is_weekend,

        -- === Entity Attributes ===
        -- TODO: Join dimension tables for descriptive attributes
        -- dim_{TODO_entity}.{TODO_entity}_name,
        -- dim_{TODO_entity}.{TODO_attribute},

        -- === Metrics from DWS ===
        -- TODO: Select the metrics needed for the dashboard
        -- metrics.order_count,
        -- metrics.unique_customers,
        -- metrics.total_amount,
        -- metrics.avg_order_value,

        -- === Derived Presentation Fields ===
        -- TODO: Add any final computed columns for display
        -- ROUND(metrics.total_amount / NULLIF(metrics.order_count, 0), 2) AS revenue_per_order,

        -- === Metadata ===
        CURRENT_TIMESTAMP AS refreshed_at_utc

    FROM metrics

    -- TODO: Join dimension tables
    -- LEFT JOIN {{ ref('dim_date') }} AS dim_date
    --     ON metrics.date_sk = dim_date.date_sk
    -- LEFT JOIN {{ ref('{TODO_dim_table}') }} AS dim_{TODO_entity}
    --     ON metrics.{TODO_entity}_sk = dim_{TODO_entity}.{TODO_entity}_sk

)

SELECT * FROM enriched
