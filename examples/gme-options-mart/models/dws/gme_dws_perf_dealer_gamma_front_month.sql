-- gme_dws_perf_dealer_gamma_front_month — front-month dealer net gamma in SHARES per 1%.
-- No `spot² · 0.01` factor (closes Phase B.5 finding 2: the unit factor alone is
-- insufficient to distinguish from net_gex; scope = front_expiry_flag = TRUE is the
-- load-bearing distinction).
-- gex_zero_cross_strike: strike-axis diagnostic. Deterministic tie-break = crossing
-- nearest current spot; on equidistant ties, the LOWER strike. Exact-zero substitution:
-- K* = K_above when cum_gex_above = 0; K* = K_below when cum_gex_below = 0; only when
-- both endpoints are strictly non-zero do we apply the linear-interpolation formula.

with greeks as (
    select * from {{ ref('gme_dwd_options_chain_greeks') }}
    where front_expiry_flag = true and gamma_bs is not null
),

dealer_sum as (
    select
        trading_date,
        max(spot) as spot,
        sum(gamma_bs * open_interest * 100.0 * sign_dealer) as dealer_net_gamma,
        count(*) as n_rows_used
    from greeks
    group by 1
),

per_strike as (
    select
        trading_date,
        strike,
        max(spot) as spot,
        sum(gamma_bs * open_interest * 100.0 * pow(spot, 2) * 0.01 * sign_dealer) as per_strike_gex
    from greeks
    group by 1, 2
),

with_cum as (
    select
        trading_date,
        strike,
        spot,
        per_strike_gex,
        sum(per_strike_gex) over (
            partition by trading_date
            order by strike
            rows between unbounded preceding and current row
        ) as cum_gex
    from per_strike
),

adjacent as (
    select
        trading_date,
        spot,
        lag(strike)  over (partition by trading_date order by strike) as k_below,
        strike                                                          as k_above,
        lag(cum_gex) over (partition by trading_date order by strike) as cum_gex_below,
        cum_gex                                                         as cum_gex_above
    from with_cum
),

candidates as (
    select
        trading_date,
        spot,
        k_below,
        k_above,
        cum_gex_below,
        cum_gex_above,
        case
            when cum_gex_above = 0 then k_above
            when cum_gex_below = 0 then k_below
            else k_below - cum_gex_below * (k_above - k_below)
                            / nullif(cum_gex_above - cum_gex_below, 0)
        end as k_star
    from adjacent
    where k_below is not null
      and (
          (cum_gex_above > 0 and cum_gex_below < 0)
       or (cum_gex_above < 0 and cum_gex_below > 0)
       or cum_gex_above = 0
       or cum_gex_below = 0
      )
),

ranked as (
    select
        trading_date,
        spot,
        k_star,
        row_number() over (
            partition by trading_date
            order by abs(k_star - spot) asc, k_star asc
        ) as rn,
        count(*) over (partition by trading_date) as n_candidates
    from candidates
    where k_star is not null
),

zero_cross as (
    select trading_date, k_star as gex_zero_cross_strike, n_candidates
    from ranked
    where rn = 1
)

select
    d.trading_date,
    d.dealer_net_gamma,
    d.n_rows_used,
    'front_month_only'::varchar as scope_label,
    z.gex_zero_cross_strike,
    coalesce(z.n_candidates, 0) as gex_zero_cross_n_candidates,
    cast(strftime(d.trading_date, '%Y%m%d') as integer) as date_sk
from dealer_sum d
left join zero_cross z using (trading_date)
