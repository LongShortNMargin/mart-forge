-- dim_date covers 2020-01-01 → 2100-12-31. is_trading_day = Mon-Fri AND NOT in
-- dim_holidays. The wide upper bound (2100) keeps the relationships test in
-- schema.yml satisfied for the synthetic test fixtures planted at 2098-2099
-- (TC-16, TC-17) which are intentionally placed far past the real-data range
-- so steady-state queries against current dates never touch them.
--
-- The dim_date OFFSET-251 lookup in gme_dws_perf_implied_vol relies on this
-- table to pin the iv_rank percentile window to exactly 252 prior trading days
-- (BRD §B-3).

with calendar as (
    select cast(d as date) as calendar_date
    from unnest(generate_series(date '2020-01-01', date '2100-12-31', interval '1 day')) as t(d)
),

holidays as (
    select holiday_date from {{ ref('dim_holidays_seed') }}
),

joined as (
    select
        cast(strftime(c.calendar_date, '%Y%m%d') as integer) as date_sk,
        c.calendar_date,
        extract(isodow from c.calendar_date) as iso_dow,
        (extract(isodow from c.calendar_date) between 1 and 5
         and h.holiday_date is null) as is_trading_day,
        date_trunc('week', c.calendar_date)  as week_start,
        date_trunc('month', c.calendar_date) as month_start
    from calendar c
    left join holidays h on h.holiday_date = c.calendar_date
)

select
    date_sk,
    calendar_date,
    is_trading_day,
    cast(iso_dow as integer) as day_of_week,
    cast(week_start as date)  as week_start,
    cast(month_start as date) as month_start
from joined
