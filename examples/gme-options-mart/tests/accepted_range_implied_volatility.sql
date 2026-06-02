-- TC-24 (Phase D /mart-dqc gap-fill): Accepted Range on gme_dwd_options_chain.
-- TDD §T-18 row accepted_range_iv: implied_volatility IS NULL OR (>0 AND <10).
-- DWD coalesces sub-1e-4 IVs to NULL (treated as the standard "implied_volatility
-- not reported"), so an IV value above 10 (i.e. 1000% annualised) would only
-- arise from a data-quality regression.

select trading_date, expiry_date, strike, option_type, implied_volatility
from {{ ref('gme_dwd_options_chain') }}
where implied_volatility is not null
  and not (implied_volatility > 0 and implied_volatility < 10)
