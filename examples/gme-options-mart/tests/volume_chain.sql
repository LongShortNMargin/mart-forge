-- TC-22 (Phase D /mart-dqc gap-fill): Volume on gme_ods_options_chain_snapshot.
-- TDD §T-18 row volume_chain: row count within ±20% of the trailing 5-day
-- median row count for the same trading_date series. The test no-ops on
-- trading_dates that lack 5 prior non-fixture trading_dates of history
-- (cold-start window) — this is correct behaviour for a fixture seed
-- carrying ≤2 real trading_dates and is the same cold-start logic used by
-- iv_rank's `provisional` label.
--
-- Fixture rows (pull_ts_utc > now(), anchored to 2098-2099) are excluded so
-- the trailing-window picker never sees synthetic far-future trading_dates.

with real_chain as (
    select trading_date, pull_ts_utc
    from {{ ref('gme_ods_options_chain_snapshot') }}
    where pull_ts_utc <= now()
),

daily_counts as (
    select trading_date, count(*) as row_count
    from real_chain
    group by 1
),

with_prior_median as (
    select
        d.trading_date,
        d.row_count,
        (
            select median(d2.row_count)
            from daily_counts d2
            where d2.trading_date < d.trading_date
              and d2.trading_date >= d.trading_date - interval '14 days'
        ) as trailing_median,
        (
            select count(*)
            from daily_counts d3
            where d3.trading_date < d.trading_date
              and d3.trading_date >= d.trading_date - interval '14 days'
        ) as n_prior_days
    from daily_counts d
)

select
    trading_date,
    row_count,
    trailing_median,
    n_prior_days
from with_prior_median
where n_prior_days >= 5
  and trailing_median is not null
  and trailing_median > 0
  and (row_count < trailing_median * 0.8 or row_count > trailing_median * 1.2)
