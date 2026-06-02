-- TC-08: T3.4 structural predicate — front-month-only model has fewer rows than full-chain
-- model whenever back-month rows exist, and scope_label differs.

with fm as (
    select trading_date, n_rows_used as fm_rows, scope_label as fm_label
    from {{ ref('gme_dws_perf_dealer_gamma_front_month') }}
),
fc as (
    select trading_date, n_rows_used as fc_rows, scope_label as fc_label
    from {{ ref('gme_dws_perf_dealer_gamma') }}
)
select fm.trading_date, fm.fm_rows, fc.fc_rows, fm.fm_label, fc.fc_label
from fm
inner join fc using (trading_date)
where fm.fm_label = fc.fc_label
   or (fc.fc_rows > fm.fm_rows + 0 and not (fc.fc_rows > fm.fm_rows))
