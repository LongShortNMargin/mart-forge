-- TC-08: T3.4 structural predicate — front-month-only model has fewer rows than full-chain
-- model whenever back-month rows exist, and scope_label differs.
--
-- Closes Phase C.5 finding 1: the round-1 OR clause `(fc_rows > fm_rows + 0 AND NOT (fc_rows > fm_rows))`
-- collapsed to FALSE, leaving only the label check. The row-count check is the load-bearing
-- half of T3.4 — labels can drift to match by typo, but row counts cannot match when one
-- model filters on front_expiry_flag = TRUE and the other doesn't, UNLESS back-month OI is
-- zero. The new predicate asserts: if back-month rows exist for a trading_date in the DWD,
-- then the front-month-only model MUST have strictly fewer rows than the full-chain model.

with fm as (
    select trading_date, n_rows_used as fm_rows, scope_label as fm_label
    from {{ ref('gme_dws_perf_dealer_gamma_front_month') }}
),
fc as (
    select trading_date, n_rows_used as fc_rows, scope_label as fc_label
    from {{ ref('gme_dws_perf_dealer_gamma') }}
),
back_month as (
    select distinct trading_date
    from {{ ref('gme_dwd_options_chain_greeks') }}
    where front_expiry_flag = false
)
select fm.trading_date, fm.fm_rows, fc.fc_rows, fm.fm_label, fc.fc_label
from fm
inner join fc using (trading_date)
where fm.fm_label = fc.fc_label
   or (
        fc.fc_rows <= fm.fm_rows
        and fm.trading_date in (select trading_date from back_month)
   )
