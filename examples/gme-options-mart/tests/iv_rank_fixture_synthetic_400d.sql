-- TC-17: synthetic 400-trading-day bimodal iv30 series fed through the
-- production gme_dws_perf_implied_vol model via seeds/test_fixtures/.
--
-- Fixture (per iv_rank_synthetic_400d_chain.csv + iv_rank_synthetic_400d_price.csv):
--   N=0..199   ⇒ iv30 = 0.5 (200 high days)
--   N=200..399 ⇒ iv30 = 0.3 (200 low days)
--   trading_date = 2098-01-01 + N days. Last row 2099-02-04.
--
-- For the last fixture row (2099-02-04, iv30=0.3) the dim_date OFFSET-251
-- lookup lands around 2098-02-04 (dim_date now spans 2020-2100 — widened
-- by this round to keep relationships tests green for the 2098-2099
-- fixture, see models/dim/dim_date.sql header). The b2 window therefore
-- captures ~365 fixture rows, of which ~199 have iv30=0.3 and qualify
-- under b2.iv30 <= 0.3, giving iv_rank ≈ 199/365 ≈ 54.5 % (materialised
-- value 56.53 % within trading-day-count rounding).
--
-- A broken percent_rank-by-magnitude (the round-1 form) would put the last
-- row's iv30=0.3 at the tied minimum and return 0 %. The 500-calendar-day
-- regression that round-1 round-2 introduced is invisible in this fixture
-- (both windows swallow >252 prior fixture rows here); the catastrophic
-- bracketing/percentile failure modes both produce values well outside
-- [40, 60] %, so the band is wide enough to catch them while tolerant to
-- small trading-day-count jitter inside the correct implementation.

select trading_date, iv30, iv_rank_lookback_days, iv_rank, iv_rank_label
from {{ ref('gme_dws_perf_implied_vol') }}
where trading_date = cast('2099-02-04' as date)
  and (
        iv_rank is null
     or iv_rank < 40.0
     or iv_rank > 60.0
     or iv_rank_label is distinct from 'final'
  )
