-- ODS Layer: Raw ingestion with provenance tracking
-- Materialization: incremental (delete+insert)
--
-- TODO: Replace placeholders marked with {TODO_...}
-- TODO: Update source(), unique_key, and partition column

{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='{TODO_unique_key}',  -- e.g., 'transaction_id'
        partition_by='{TODO_partition_column}'  -- e.g., 'event_date'
    )
}}

WITH source_data AS (

    SELECT
        -- === Business Columns ===
        -- TODO: Map source columns here
        -- src.column_1,
        -- src.column_2,

        -- === Provenance Columns ===
        '{TODO_provider_name}'              AS provider,
        CURRENT_TIMESTAMP                   AS pull_ts_utc,
        '{{ run_started_at }}'              AS run_id

    FROM {{ source('{TODO_source_schema}', '{TODO_source_table}') }} AS src

    {% if is_incremental() %}
    WHERE src.{TODO_partition_column} >= (
        SELECT MAX({TODO_partition_column})
        FROM {{ this }}
    )
    {% endif %}

)

SELECT * FROM source_data
