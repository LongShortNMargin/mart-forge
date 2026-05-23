{{
  config(
    materialized='incremental',
    unique_key='fact_sk',
    incremental_strategy='delete+insert'
  )
}}

{#
  DWD Model Template — Cleaned Facts with Business Keys

  Rules:
  - Business key deduplication from ODS
  - Native fields: pass-through with field mapping (no computation)
  - Derived fields: explicit SQL/formula from TDD T-8 calculation column
  - Surrogate keys: native md5 hash — no external package dependency
  - Natural keys preserved for lineage
  - Source_type classification per metric column (native/derived/hybrid)
  - Explicit column list — no SELECT *
#}

with ods_source as (
    select
        record_id,
        pull_date,
        -- Add explicit source columns from TDD T-5/T-6 here
        provider,
        pull_ts_utc,
        quote_ts_utc,
        run_id
    from {{ ref('prefix_ods_source_entity') }}
    {% if is_incremental() %}
    where pull_date >= '{{ var("partition_date", (modules.datetime.datetime.now() - modules.datetime.timedelta(days=1)).strftime("%Y-%m-%d")) }}'
    {% endif %}
),

deduped as (
    select
        record_id,
        pull_date,
        provider,
        pull_ts_utc,
        quote_ts_utc,
        run_id,
        row_number() over (
            partition by record_id, pull_date
            order by pull_ts_utc desc
        ) as _dedup_rank
    from ods_source
),

with_keys as (
    select
        -- Surrogate key (native hash — no external dependency)
        md5(cast(record_id as varchar) || '|' || cast(pull_date as varchar)) as fact_sk,

        -- Dimension foreign keys (unknown member -1 if NULL)
        coalesce(d.date_sk, -1) as date_key,

        -- Native metric columns: pass-through from TDD T-8
        -- s.source_field as metric_name,

        -- Derived metric columns: explicit SQL from TDD T-8
        -- s.field_a * s.field_b as derived_metric,

        -- Provenance (carried from ODS)
        s.provider,
        s.pull_ts_utc,
        s.quote_ts_utc,
        s.run_id

    from deduped s
    left join {{ ref('prefix_dim_date') }} d
        on s.pull_date = d.calendar_date
    where s._dedup_rank = 1
)

select
    fact_sk,
    date_key,
    provider,
    pull_ts_utc,
    quote_ts_utc,
    run_id
from with_keys
