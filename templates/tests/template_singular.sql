-- Singular test: <one-line description of what this test checks>
-- Pass criterion: this query returns ZERO rows.
-- Naming convention: <control_id>_<table>.sql
--   e.g., freshness_gme_ods_options_chain.sql
--         no_dupes_gme_dwd_option_contract_di.sql

select
    <grouping_columns>,
    count(*) as violation_count
from {{ ref('<model_name>') }}
where <condition_that_should_be_false>
group by <grouping_columns>
having count(*) > 0
