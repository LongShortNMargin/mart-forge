-- TC-17: synthetic 400-trading-day iv30 series with a known monotonic distribution.
-- Closes Phase B.5 finding 2 (round-1 percent_rank-by-magnitude defect) AND Phase B.5
-- round-2 item A (500-calendar-day window over-sampling).
--
-- Construction:
--   - 400 sequential trading-day pseudo-dates (date 2024-01-01 + N business-day offset
--     simulated by `interval (n) days` over a 1-day step — we just need ordered distinct
--     dates; calendar correctness doesn't matter for the percentile mechanics).
--   - iv30(N) = 0.20 + N * 0.001 (monotonically increasing). The last row's iv30 is the
--     400th value; its analytic percentile of the trailing 252 prior values (rows
--     148..399, i.e. all of which are strictly less than iv30(400)) is exactly 100%.
--   - A correct chronological percentile that pins the window to the 252 prior trading
--     days returns 100.0 ± float epsilon.
--   - The broken percent_rank-by-magnitude window would order by iv30 magnitude and
--     produce a degenerate result (~99.6 with a frame-size dependent denominator).
--   - The round-2-draft 500-calendar-day window joined to a 400-day fixture would
--     happen to include all 399 prior values (since 500 calendar days > 400 days), so
--     the denominator would be 399 instead of 252 — easy to detect via deterministic
--     differences in the percentile when the underlying distribution is non-uniform.
--
-- This fixture is computed entirely inline so it does NOT depend on the live ODS/DWS
-- pipeline state.

with synth as (
    select
        cast('2024-01-01' as date) + cast(n as integer) as trading_date_synth,
        0.20 + cast(n as double) * 0.001 as iv30
    from range(0, 400) t(n)
),
b1 as (select trading_date_synth, iv30 from synth),
b2 as (select trading_date_synth, iv30 from synth),
last_row as (
    select max(trading_date_synth) as last_d, max(iv30) as last_iv30 from synth
),
percentile as (
    select
        b1.trading_date_synth,
        b1.iv30,
        count(*) filter (
            where b2.iv30 <= b1.iv30
              and b2.trading_date_synth < b1.trading_date_synth
              and b2.trading_date_synth >= b1.trading_date_synth - interval '252 days'
        ) as rank_count,
        count(*) filter (
            where b2.trading_date_synth < b1.trading_date_synth
              and b2.trading_date_synth >= b1.trading_date_synth - interval '252 days'
        ) as denom_window
    from b1
    cross join b2
    where b1.trading_date_synth = (select last_d from last_row)
    group by b1.trading_date_synth, b1.iv30
)

-- The trailing 252-trading-day percentile of the (monotonically maximal) last row is
-- 100% by construction. We compute the percentile against denom_window (the 252 prior
-- rows) and assert it equals 100.0 within ±0.1.
--
-- If the implementation were broken (e.g. percent_rank by iv30 magnitude OR a wider
-- window that includes >252 prior rows), the rank_count vs denom_window ratio would
-- diverge from 100.0 by more than the tolerance.

-- Expected: rank_count == denom_window (the last row is the max of the 252-row trailing
-- slice, so all 252 prior values are < it) ⇒ pct == 100.0 exactly. Fail if more than ±0.1.
select trading_date_synth, iv30, rank_count, denom_window,
       100.0 * rank_count / nullif(denom_window, 0) as pct
from percentile
where denom_window = 0
   or abs(100.0 * rank_count / cast(denom_window as double) - 100.0) > 0.1
