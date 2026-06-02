-- TC-21 (Phase D /mart-dqc gap-fill): Freshness on gme_ods_price_history.
-- TDD §T-18 row freshness_price: same BRD L-7 inequality as freshness_chain,
-- applied to the EOD price series.

with most_recent_session_close as (
    select max(calendar_date + interval '21 hours') as ts_utc
    from {{ ref('dim_date') }}
    where is_trading_day = true
      and calendar_date + interval '21 hours' <= now()
),

latest_real_pull as (
    select max(pull_ts_utc) as pull_ts
    from {{ ref('gme_ods_price_history') }}
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
