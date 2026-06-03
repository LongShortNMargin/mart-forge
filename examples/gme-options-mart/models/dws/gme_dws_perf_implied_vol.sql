-- gme_dws_perf_implied_vol — IV30, HV20, IV-rank (chronological rolling 252-trading-day
-- percentile).
--
-- iv30: linear interpolation in total variance (σ²·t) of OI-weighted ATM IV
-- (|strike/spot − 1| ≤ 0.05) to a constant 30-cal-day tenor. NULL-safe: numerator and
-- denominator restricted to the same `sigma IS NOT NULL` rowset (closes Phase B.5
-- finding 5).
--
-- iv_rank: chronological rolling 252-trading-day percentile (closes Phase B.5 finding 2
-- + round-2 item A). The b2 join window is bounded by a dim_date OFFSET-251 lookup,
-- pinning to exactly 252 prior trading days per BRD §B-3 strict contract.

{{ config(materialized='table') }}

with chain as (
    select * from {{ ref('gme_dwd_options_chain_greeks') }}
    where sigma is not null
      and time_to_expiry_years > 0
),

atm as (
    select
        trading_date,
        expiry_date,
        time_to_expiry_years,
        sum(open_interest * sigma) /
            nullif(sum(case when sigma is not null then open_interest else 0 end), 0)
            as iv_atm
    from chain
    where abs(strike / nullif(spot, 0) - 1.0) <= 0.05
    group by 1, 2, 3
),

-- Closes Phase C.5 finding 3: the prior `ranked_expiries` ROW_NUMBER ordered
-- ALL near-side expiries (T <= 30/365) before ALL far-side. On a multi-weekly
-- chain (3d/10d/17d/24d/31d/38d), rn=2 fell to another near-side expiry,
-- forcing the interpolation to extrapolate. Splitting into separate near/far
-- CTEs and FULL JOIN-ing pins (T_near, T_far) to the actual bracketing pair.
near as (
    select trading_date, time_to_expiry_years as t_years, iv_atm,
           row_number() over (
               partition by trading_date order by time_to_expiry_years desc
           ) as rn
    from atm
    where iv_atm is not null
      and time_to_expiry_years <= 30.0/365.0
),

far as (
    select trading_date, time_to_expiry_years as t_years, iv_atm,
           row_number() over (
               partition by trading_date order by time_to_expiry_years asc
           ) as rn
    from atm
    where iv_atm is not null
      and time_to_expiry_years > 30.0/365.0
),

near_far as (
    select
        coalesce(n.trading_date, f.trading_date) as trading_date,
        n.t_years as t_near,
        n.iv_atm  as iv_near,
        f.t_years as t_far,
        f.iv_atm  as iv_far
    from (select * from near where rn = 1) n
    full outer join (select * from far where rn = 1) f using (trading_date)
),

iv30_per_date as (
    select
        trading_date,
        case
            when t_far is null and iv_near is not null then iv_near
            when t_near is null then null
            when t_far is not null and (t_far - t_near) != 0 then sqrt(
                (pow(iv_near, 2) * t_near
                 + (pow(iv_far, 2) * t_far - pow(iv_near, 2) * t_near)
                   * ((30.0/365.0 - t_near) / nullif(t_far - t_near, 0))
                ) / (30.0/365.0)
            )
            else iv_near
        end as iv30
    from near_far
),

hv as (
    select
        trading_date,
        stddev_samp(log_return_1d) over (
            order by trading_date rows between 19 preceding and current row
        ) * sqrt(252) as hv20
    from {{ ref('gme_dwd_price_eod') }}
),

base as (
    select
        i.trading_date,
        i.iv30,
        coalesce(h.hv20, null) as hv20
    from iv30_per_date i
    left join hv h on h.trading_date = i.trading_date
),

with_lookback as (
    select
        b1.trading_date,
        b1.iv30,
        b1.hv20,
        count(b1.iv30) over (
            order by b1.trading_date rows between 251 preceding and current row
        ) as iv_rank_lookback_days
    from base b1
),

percentile as (
    -- Chronological rolling 252-trading-day percentile.
    -- The dim_date OFFSET-251 lookup (closes Phase B.5 round-2 item A) pins the join
    -- slice to exactly 252 prior trading days per BRD §B-3.
    select
        b1.trading_date,
        count(*) filter (where b2.iv30 <= b1.iv30 and b2.trading_date < b1.trading_date)
            as rank_count,
        count(*) filter (where b2.trading_date < b1.trading_date)
            as denom
    from base b1
    left join base b2
      on b2.trading_date >= (
            select calendar_date
            from {{ ref('dim_date') }}
            where is_trading_day = true
              and calendar_date < b1.trading_date
            order by calendar_date desc
            offset 251 limit 1
         )
     and b2.trading_date < b1.trading_date
     and b2.iv30 is not null
    where b1.iv30 is not null
    group by b1.trading_date
)

select
    w.trading_date,
    w.iv30,
    w.hv20,
    w.iv_rank_lookback_days,
    case
        when w.iv_rank_lookback_days >= 252 then 100.0 * p.rank_count / nullif(p.denom, 0)
        else null
    end as iv_rank,
    case when w.iv_rank_lookback_days >= 252 then 'final' else 'provisional' end as iv_rank_label,
    cast(strftime(w.trading_date, '%Y%m%d') as integer) as date_sk
from with_lookback w
left join percentile p using (trading_date)
