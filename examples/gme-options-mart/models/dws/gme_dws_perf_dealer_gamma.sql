-- gme_dws_perf_dealer_gamma — full-chain dealer net GEX in USD per 1% spot move.
-- scope = ALL expiries. dealer_net_gamma_front_month is a SEPARATE table with
-- scope = front_expiry_flag = TRUE; the structural distinction is what makes T3.4 honest
-- (closes Phase B.5 finding 2 / predecessor bae4af2 dealer_net_gamma == net_gex bug).

select
    trading_date,
    sum(gamma_bs * open_interest * 100.0 * pow(spot, 2) * 0.01 * sign_dealer) as net_gex,
    count(*)              as n_rows_used,
    'full_chain'::varchar as scope_label,
    cast(strftime(trading_date, '%Y%m%d') as integer) as date_sk
from {{ ref('gme_dwd_options_chain_greeks') }}
where gamma_bs is not null
group by 1
