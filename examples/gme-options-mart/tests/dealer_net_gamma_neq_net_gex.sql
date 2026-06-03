-- TC-07: T3.4 numerical predicate (Phase A.5 item B).
-- abs(dealer_net_gamma - net_gex / (spot²·0.01)) > 0.01 * abs(dealer_net_gamma)
-- whenever back-month OI > 0 — i.e., the front-month-only sum differs from a unit-
-- rescaled full-chain sum by more than 1% of dealer_net_gamma. If back-month OI is zero
-- the test is unconditionally satisfied.

with fm as (
    select trading_date, dealer_net_gamma, n_rows_used as fm_rows
    from {{ ref('gme_dws_perf_dealer_gamma_front_month') }}
),
fc as (
    select trading_date, net_gex, n_rows_used as fc_rows
    from {{ ref('gme_dws_perf_dealer_gamma') }}
),
spot as (
    select trading_date, close_px as spot from {{ ref('gme_dwd_price_eod') }}
),
joined as (
    select
        fm.trading_date,
        fm.dealer_net_gamma,
        fc.net_gex,
        spot.spot,
        fc.fc_rows - fm.fm_rows as back_month_rows,
        abs(fm.dealer_net_gamma - fc.net_gex / nullif(pow(spot.spot, 2) * 0.01, 0))
            as residual,
        0.01 * abs(fm.dealer_net_gamma) as epsilon
    from fm
    inner join fc using (trading_date)
    inner join spot using (trading_date)
)

select trading_date, dealer_net_gamma, net_gex, residual, epsilon, back_month_rows
from joined
where back_month_rows > 0
  and residual <= epsilon
  and abs(dealer_net_gamma) > 1e-9
