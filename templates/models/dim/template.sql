-- DIM Layer: Seed-backed dimension table
-- Materialization: table
--
-- TODO: Replace placeholders marked with {TODO_...}
-- TODO: Define surrogate key and natural key columns

{{
    config(
        materialized='table'
    )
}}

WITH seed_source AS (

    SELECT *
    FROM {{ ref('{TODO_seed_name}') }}
    -- e.g., ref('dim_date') or ref('seed_product_categories')

),

with_surrogate_key AS (

    SELECT
        -- === Surrogate Key ===
        ROW_NUMBER() OVER (ORDER BY {TODO_natural_key}) AS {TODO_entity}_sk,

        -- === Natural Key ===
        {TODO_natural_key},

        -- === Dimension Attributes ===
        -- TODO: List dimension columns here
        -- column_1,
        -- column_2,
        -- column_3,

        -- === Metadata ===
        CURRENT_TIMESTAMP AS loaded_at_utc

    FROM seed_source

)

SELECT * FROM with_surrogate_key
