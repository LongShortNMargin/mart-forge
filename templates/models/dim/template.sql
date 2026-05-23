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
  - Explicit column list — no SELECT *

  For Type 2 dimensions, add:
    effective_from, effective_to, is_current columns
#}

with seed_data as (
    select
        entity_id,
        entity_name
    from {{ ref('seed_dim_entity') }}
),

unknown_member as (
    select
        -1 as entity_sk,
        'UNKNOWN' as entity_id,
        'Unknown' as entity_name
),

numbered as (
    select
        row_number() over (order by entity_id) as entity_sk,
        entity_id,
        entity_name
    from seed_data
)

select entity_sk, entity_id, entity_name from numbered
union all
select entity_sk, entity_id, entity_name from unknown_member
