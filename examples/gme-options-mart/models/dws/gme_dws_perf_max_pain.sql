-- gme_dws_perf_max_pain — per (trading_date, expiry_date) max-pain strike.
-- Closes Phase B.5 finding 1: pain(K) = SUM_calls(oi · max(0, K - K_under))
--                              + SUM_puts(oi · max(0, K_under - K))
-- K = candidate underlying close; K_under = option strike. Calls go ITM when K > K_under;
-- puts go ITM when K < K_under (ITM dollar pain, NOT OTM distance).
-- Per-side strike dedup happens BEFORE the cross-join with the candidate-strike universe
-- (closes T3.3 / predecessor bae4af2 cross-join cardinality bug).

with dedup as (
    select
        trading_date,
        expiry_date,
        strike,
        option_type,
        sum(open_interest) as oi
    from {{ ref('gme_dwd_options_chain') }}
    group by 1, 2, 3, 4
),

universe as (
    select distinct trading_date, expiry_date, strike as candidate_k
    from dedup
),

pain as (
    select
        u.trading_date,
        u.expiry_date,
        u.candidate_k,
        sum(case when d.option_type = 'call' then d.oi * greatest(0, u.candidate_k - d.strike) else 0 end)
          + sum(case when d.option_type = 'put'  then d.oi * greatest(0, d.strike - u.candidate_k) else 0 end) as pain_value
    from universe u
    inner join dedup d
      on d.trading_date = u.trading_date
     and d.expiry_date  = u.expiry_date
    group by 1, 2, 3
),

ranked as (
    select
        trading_date,
        expiry_date,
        candidate_k,
        pain_value,
        row_number() over (
            partition by trading_date, expiry_date
            order by pain_value asc, candidate_k asc
        ) as rn
    from pain
),

n_strikes as (
    select trading_date, expiry_date, count(distinct strike) as n_distinct_strikes
    from dedup
    group by 1, 2
)

select
    r.trading_date,
    r.expiry_date,
    n.n_distinct_strikes,
    r.candidate_k as max_pain_strike,
    cast(strftime(r.trading_date, '%Y%m%d') as integer) as date_sk,
    cast(strftime(r.expiry_date,  '%Y%m%d') as integer) as expiry_date_sk
from ranked r
inner join n_strikes n using (trading_date, expiry_date)
where r.rn = 1
