-- TC-20 (Phase D /mart-dqc gap-fill): Freshness on gme_ods_options_chain_snapshot.
-- TDD §T-18 row freshness_chain: BRD L-7 single inequality
-- `MAX(pull_ts_utc) - most_recent_session_close <= 26h` evaluated against the
-- most-recent-in-the-past trading session close, where pull_ts_utc <= now()
-- excludes far-future fixture rows (Phase C.5 round-3 latest_date pattern).
--
-- Test fails iff a real (pull_ts_utc <= now()) pull's latest sample is more
-- than 26 hours older than the most recent past trading session close.

with most_recent_session_close as (
    select max(calendar_date + interval '21 hours') as ts_utc
    from {{ ref('dim_date') }}
    where is_trading_day = true
      and calendar_date + interval '21 hours' <= now()
),

latest_real_pull as (
    select max(pull_ts_utc) as pull_ts
    from {{ ref('gme_ods_options_chain_snapshot') }}
    where pull_ts_utc <= now()
)

select
    p.pull_ts,
    m.ts_utc as most_recent_session_close_ts_utc,
    extract(epoch from (m.ts_utc - p.pull_ts)) / 3600.0 as lag_hours
from latest_real_pull p
cross join most_recent_session_close m
where p.pull_ts is not null
  and m.ts_utc is not null
  and extract(epoch from (m.ts_utc - p.pull_ts)) / 3600.0 > 26
