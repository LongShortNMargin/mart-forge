-- TC-06: max_pain_strike must be in the distinct strike set for (trading_date, expiry_date).
-- Closes T3.3 / predecessor bae4af2 cross-join cardinality bug.

with strikes as (
    select distinct trading_date, expiry_date, strike
    from {{ ref('gme_dwd_options_chain') }}
)

select mp.trading_date, mp.expiry_date, mp.max_pain_strike
from {{ ref('gme_dws_perf_max_pain') }} mp
left join strikes s
    on s.trading_date = mp.trading_date
   and s.expiry_date  = mp.expiry_date
   and s.strike       = mp.max_pain_strike
where s.strike is null
