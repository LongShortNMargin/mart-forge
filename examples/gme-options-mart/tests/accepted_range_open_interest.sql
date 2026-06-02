-- TC-23 (Phase D /mart-dqc gap-fill): Accepted Range on gme_dwd_options_chain.
-- TDD §T-18 row accepted_range_oi: open_interest >= 0 (DWD coalesces nulls
-- to 0 and the ODS-to-DWD CTE rejects open_interest < 0, so any failure
-- here would indicate either a DWD cleaning regression or an upstream
-- contract drift).

select trading_date, expiry_date, strike, option_type, open_interest
from {{ ref('gme_dwd_options_chain') }}
where open_interest < 0
