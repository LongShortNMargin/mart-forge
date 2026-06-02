-- TC-16: asymmetric synthetic chain — 1,000 calls @ K=20 and 2,000 puts @ K=30
-- at trading_date=2099-12-31 / expiry_date=2100-01-31. Fixture lives in
-- seeds/test_fixtures/max_pain_asymmetric_chain.csv and is plumbed through the
-- production ODS → DWD → DWS pipeline via gme_ods_options_chain_snapshot.
--
-- Correct ITM-dollar-pain formula:
--   pain(K=20) = 1000 * max(0, 20-20) + 2000 * max(0, 30-20) = 20,000
--   pain(K=30) = 1000 * max(0, 30-20) + 2000 * max(0, 30-30) = 10,000
--   argmin ⇒ K=30.
--
-- Broken (round-1) swapped-roles formula:
--   pain(K=20) = 1000 * max(0, 20-20) + 2000 * max(0, 20-30) = 0
--   pain(K=30) = 1000 * max(0, 20-30) + 2000 * max(0, 30-30) = 0
--   tied at 0 ⇒ tie-break picks K=20 (lower).
--
-- This test reads gme_dws_perf_max_pain. A regression in the formula
-- (or in the per-side dedup that closes the cross-join cardinality bug) flips
-- the answer away from 30.

select trading_date, expiry_date, max_pain_strike
from {{ ref('gme_dws_perf_max_pain') }}
where trading_date = cast('2099-12-31' as date)
  and expiry_date  = cast('2100-01-31' as date)
  and max_pain_strike is distinct from 30.0
