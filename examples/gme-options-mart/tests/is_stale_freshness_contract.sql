-- TC-12 (carry-forward from TDD §T-19) / TC-25 (Phase D /mart-dqc gap-fill):
-- ADS is_stale must equal NOT (pull_lag_hours BETWEEN 0 AND 26).
-- This is the same BRD L-7 inequality that TC-20/TC-21 evaluate at the ODS
-- layer; here it's enforced at the view-of-record so any future drift in
-- the ADS is_stale formula vs the BRD contract surfaces as a test failure.

select
    trading_date,
    pull_lag_hours,
    is_stale,
    not (pull_lag_hours >= 0 and pull_lag_hours <= 26) as expected_is_stale
from {{ ref('gme_ads_market_dashboard') }}
where pull_lag_hours is not null
  and is_stale is not null
  and is_stale != (not (pull_lag_hours >= 0 and pull_lag_hours <= 26))
