{#
  Singular Test Template

  Naming convention: test_{model}_{what_it_checks}
  Example: test_dwd_orders_no_future_dates

  A singular test returns rows that FAIL the check.
  Zero rows returned = test passes.
  Any rows returned = test fails.
#}

-- test_{model}_{check_description}
-- Validates: {description of what this test checks}
-- Control class: {PK Integrity / FK Integrity / Freshness / Completeness / Accepted Ranges / Duplicate Detection / Null-Rate / Business Reconciliation}
-- Severity: {error / warn}

select *
from {{ ref('model_name') }}
where
    -- Example: check for future dates (should not exist)
    -- pull_date > current_date

    -- Example: check PK uniqueness
    -- record_id in (
    --     select record_id
    --     from {{ ref('model_name') }}
    --     group by record_id
    --     having count(*) > 1
    -- )

    -- Example: freshness check
    -- (select max(pull_ts_utc) from {{ ref('model_name') }})
    --   < current_timestamp - interval '24 hours'

    -- Example: null rate threshold (>10% nulls in a column)
    -- (select count(*) filter (where column_name is null)::float / count(*)
    --  from {{ ref('model_name') }}) > 0.10

    false  -- Replace with actual check logic
