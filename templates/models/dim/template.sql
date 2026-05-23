{{
  config(
    materialized='table'
  )
}}

{#
  DIM Model Template — Conformed Dimension

  Rules:
  - Seed-backed where applicable
  - Unknown member row (surrogate_key = -1, all attributes = 'Unknown')
  - SCD strategy declared per attribute (Type 0 / Type 1 / Type 2)
  - Role-playing supported (e.g., dim_date as trade_date and expiry_date)

  For Type 2 dimensions, add:
    effective_from, effective_to, is_current columns
    Merge strategy in the model
#}

with seed_data as (
    select * from {{ ref('seed_dim_entity') }}
),

unknown_member as (
    select
        -1 as entity_sk,
        'UNKNOWN' as entity_id,
        'Unknown' as entity_name
        -- Add all dimension attributes with 'Unknown' default
),

final as (
    select
        -- Surrogate key (integer or hash)
        row_number() over (order by entity_id) as entity_sk,
        -- Natural key (preserved for lineage)
        entity_id,
        -- Dimension attributes
        entity_name
        -- SCD Type 2 columns (if applicable):
        -- effective_from,
        -- effective_to,
        -- is_current

    from seed_data

    union all

    select * from unknown_member
)

select * from final
