-- TC-19 (Phase D /mart-dqc gap-fill): Duplicate Detection on gme_dwd_options_chain.
-- TDD §T-18 row duplicate_detection: no duplicate
-- (trading_date, expiry_date, strike, option_type) after the ODS-to-DWD dedup.
-- Also serves as the DWD-side compound PK uniqueness assertion.

select
    trading_date,
    expiry_date,
    strike,
    option_type,
    count(*) as n_rows
from {{ ref('gme_dwd_options_chain') }}
group by 1, 2, 3, 4
having count(*) > 1
