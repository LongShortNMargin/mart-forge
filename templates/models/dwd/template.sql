-- DWD Layer: Cleaned fact table with business keys
-- Materialization: table
--
-- TODO: Replace placeholders marked with {TODO_...}
-- TODO: Add dimension joins and business logic

{{
    config(
        materialized='table'
    )
}}

WITH ods_source AS (

    SELECT *
    FROM {{ ref('{TODO_ods_table_name}') }}
    -- e.g., ref('ecom_ods_orders_raw')

),

dim_joined AS (

    SELECT
        -- === Business Keys ===
        -- TODO: Define business keys
        -- ods.order_id,
        -- ods.customer_id,

        -- === Dimension Foreign Keys ===
        -- TODO: Join to dimension tables for surrogate keys
        -- dim_date.date_sk,
        -- dim_product.product_sk,

        -- === Fact Columns (cleaned) ===
        -- TODO: Apply cleaning / transformation logic
        -- COALESCE(ods.amount, 0) AS amount,
        -- CASE WHEN ods.status IN ('completed', 'shipped') THEN 'fulfilled' ELSE ods.status END AS order_status,

        -- === Provenance (carried from ODS) ===
        ods.provider,
        ods.pull_ts_utc,
        ods.run_id

    FROM ods_source AS ods

    -- TODO: Add dimension joins
    -- LEFT JOIN {{ ref('dim_date') }} AS dim_date
    --     ON ods.event_date = dim_date.full_date
    -- LEFT JOIN {{ ref('{TODO_dim_table}') }} AS dim_{TODO_entity}
    --     ON ods.{TODO_natural_key} = dim_{TODO_entity}.{TODO_natural_key}

)

SELECT * FROM dim_joined
