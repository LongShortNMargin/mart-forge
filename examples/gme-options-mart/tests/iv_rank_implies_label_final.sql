-- TC-09: iv_rank IS NULL OR iv_rank_label = 'final'; label = 'final' iff
-- iv_rank_lookback_days >= 252. Closes T3.5 / predecessor null-without-label bug.

select trading_date, iv_rank, iv_rank_label, iv_rank_lookback_days
from {{ ref('gme_dws_perf_implied_vol') }}
where (iv_rank is not null and iv_rank_label <> 'final')
   or (iv_rank_lookback_days >= 252 and iv_rank_label <> 'final')
   or (iv_rank_lookback_days <  252 and iv_rank_label <> 'provisional')
