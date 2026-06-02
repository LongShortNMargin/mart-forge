-- TC-10: gex_zero_cross_strike IS NULL OR lies in the closed interval
-- [min(front_month strike), max(front_month strike)] (closes reviewer items C +
-- Phase B.5 finding 3).

with bounds as (
    select
        g.trading_date,
        min(g.strike) as k_min,
        max(g.strike) as k_max
    from {{ ref('gme_dwd_options_chain_greeks') }} g
    where g.front_expiry_flag = true
    group by 1
)

select fm.trading_date, fm.gex_zero_cross_strike, b.k_min, b.k_max
from {{ ref('gme_dws_perf_dealer_gamma_front_month') }} fm
left join bounds b using (trading_date)
where fm.gex_zero_cross_strike is not null
  and (
      b.k_min is null
   or fm.gex_zero_cross_strike < b.k_min
   or fm.gex_zero_cross_strike > b.k_max
  )
