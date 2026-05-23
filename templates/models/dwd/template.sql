{{
  config(
    materialized='incremental',
    unique_key=var('dwd_unique_key', ['fact_sk']),
    incremental_strategy='delete+insert'
  )
}}

{#
  DWD Model Template — Cleaned Facts with Business Keys

  Rules:
  - Business key deduplication from ODS
  - Native fields: pass-through with field mapping (no computation)
  - Derived fields: explicit SQL/formula from TDD calculation column
  - Surrogate keys generated here, never exposed to consumers
  - Natural keys preserved for lineage
  - Source_type classification per metric column (native/derived/hybrid)
  - Incremental materialization
#}

with ods_source as (
    select * from {{ ref('prefix_ods_source_entity') }}
    {% if is_incremental() %}
    where pull_date >= '{{ var("partition_date", (modules.datetime.datetime.now() - modules.datetime.timedelta(days=1)).strftime("%Y-%m-%d")) }}'
    {% endif %}
),

deduped as (
    select
        *,
        row_number() over (
            partition by {{ var('business_key_columns', 'record_id, pull_date') }}
            order by pull_ts_utc desc
        ) as _rn
    from ods_source
),

with_keys as (
    select
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['record_id', 'pull_date']) }} as fact_sk,

        -- Dimension foreign keys (point to unknown member -1 if NULL)
        coalesce(d.date_sk, -1) as date_key,

        -- Native metric columns (pass-through, no computation)
        -- source_field_1,
        -- source_field_2,

        -- Derived metric columns (explicit SQL from TDD)
        -- native_field_a * native_field_b as derived_metric_1,

        -- Provenance (carried from ODS)
        provider,
        pull_ts_utc,
        quote_ts_utc,
        run_id

    from deduped s
    left join {{ ref('prefix_dim_date') }} d
        on s.pull_date = d.calendar_date
    where s._rn = 1
)

select * from with_keys
