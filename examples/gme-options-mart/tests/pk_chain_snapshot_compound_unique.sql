-- TC-18 (Phase D /mart-dqc gap-fill): PK Integrity for gme_ods_options_chain_snapshot.
-- TDD §T-18 row pk_chain_snapshot: compound key
-- (trading_date, expiry_date, strike, option_type) must be unique and not-null.
-- schema.yml carries not_null on each column individually; this singular test
-- closes the missing compound-uniqueness check that not_null on each column
-- cannot express.

select
    trading_date,
    expiry_date,
    strike,
    option_type,
    count(*) as n_rows
from {{ ref('gme_ods_options_chain_snapshot') }}
group by 1, 2, 3, 4
having count(*) > 1
