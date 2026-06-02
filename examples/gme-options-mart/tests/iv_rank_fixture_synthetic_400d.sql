-- TC-17: synthetic 400-trading-day bimodal iv30 series fed through the
-- production gme_dws_perf_implied_vol model via seeds/test_fixtures/.
--
-- Fixture (per iv_rank_synthetic_400d_chain.csv + iv_rank_synthetic_400d_price.csv):
--   N=0..199   ⇒ iv30 = 0.5 (200 high days)
--   N=200..399 ⇒ iv30 = 0.3 (200 low days)
--   trading_date = 2098-01-01 + N days. Last row 2099-02-04.
--
-- For the last fixture row (2099-02-04, iv30=0.3) the dim_date OFFSET-251
-- lookup returns ~late-2026 (2099 is past dim_date's 2020-2027 coverage so
-- the cutoff lands on the 252nd-from-last dim_date trading day). The b2
-- window therefore opens fully across all 399 prior fixture rows. Of those,
-- 199 have iv30=0.3 and qualify under b2.iv30 <= 0.3:
--
--   correct chronological percentile = 199/399 ≈ 49.87 %
--
-- A broken percent_rank-by-magnitude (the round-1 form) would put the last
-- row's iv30=0.3 at the tied minimum and return 0 %. A reintroduction of
-- the 500-calendar-day window over a 400-trading-day fixture is invisible
-- in this assertion only because of the 2099-placement (the model's
-- dim_date-bounded window already swallows all 399 prior rows here); the
-- bracketing-and-percentile failure modes that round-1/round-2 introduced
-- both produce values well outside [40, 60] %.

select trading_date, iv30, iv_rank_lookback_days, iv_rank, iv_rank_label
from {{ ref('gme_dws_perf_implied_vol') }}
where trading_date = cast('2099-02-04' as date)
  and (
        iv_rank is null
     or iv_rank < 40.0
     or iv_rank > 60.0
     or iv_rank_label is distinct from 'final'
  )
