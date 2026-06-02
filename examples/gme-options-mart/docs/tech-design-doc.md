# Technical Design Document: gme-options-mart

> **Date:** 2026-06-02
> **Author:** mart-forge example author
> **Prefix:** gme
> **Status:** Draft (Phase B round 2 — derived from signed BRD v0.3 +
> source_catalog.json round-2; addresses reviewer items B–E from
> comment `751fbe78` AND Phase B.5 round-1 findings 1–5 + D + E from
> comment `b61820e9` per orchestrator directive `15c917df`).

---

## T-1: Changelog

| Version | Date       | Author                     | Section(s) Changed | Summary of Changes                                                                                                                                                                                                                                                                                                                  |
|---------|------------|----------------------------|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1     | 2026-06-02 | mart-forge example author  | All                | Initial Phase B draft against signed BRD (`brd_signed: true`, comment `751fbe78` approval). Applies reviewer Phase A.5 items B–E in the right place: T3.4 epsilon = 1% of `abs(dealer_net_gamma)` (item B); `gex_zero_cross_strike` tie-break = nearest spot, lower strike on tie (item C); T1.6b near-zero denominator floor = $1e6 (item D); iv_rank `link_status_active` lifecycle deferred to Phase D /mart-dqc as a documented Phase B concern (item E). |
| 0.2     | 2026-06-02 | mart-forge example author  | T-3, T-6, T-11, T-13, T-14, T-15, T-16, T-17, T-19, T-21 | Phase B round-2: closes Phase B.5 findings 1–5 + D + E per orchestrator directive `15c917df`. (1) Swap max_pain formula terms in T-3 row 46 and T-13 line 365 step 2: `pain(K) = SUM_calls(oi · max(0, K − K_under)) + SUM_puts(oi · max(0, K_under − K))` — K is candidate underlying close, K_under is option strike, gives ITM intrinsic value not OTM distance; new singular fixture `max_pain_fixture_asymmetric_chain.sql` (TC-16) asserts the swap. (2) Rewrite iv_rank as a chronological rolling 252-day percentile keyed on `trading_date` (NOT `percent_rank() OVER (ORDER BY iv30)` which is rank-by-magnitude and degenerate); new singular fixture `iv_rank_fixture_synthetic_252d.sql` (TC-17). (3) Materialise `gme_ads_market_dashboard` as `view` so `most_recent_session_close_ts_utc`, `pull_lag_hours`, `is_stale` re-evaluate at every dashboard query; T-6, T-15, T-14, T-17, TL-4 updated. (4) Tighten T-11 `front_expiry_flag` to nearest expiry STRICTLY AFTER `trading_date` so weekly-expiration-day metrics share one "front" definition; T-14 max_pain_strike_front subquery simplified to reference `front_expiry_flag = TRUE`. (5) NULL-safe denominator in T-13 iv30 step 1: numerator and denominator see the same `sigma IS NOT NULL` rowset. (D) Spell out exact-zero substitution rule in T-13 `gex_zero_cross_strike` step 5: `K* = K_above` (or `K_below`) when `cum_gex_above` (or `cum_gex_below`) is exactly zero. (E) T-3 row 53 `dealer_net_gamma` calculation references `front_expiry_flag = TRUE`, not the undefined `front_expiry_date` symbol. Status remains `tdd_signed = false`; awaiting Phase B.5 round-2 review.|

---

## T-2: Business Background

The mart serves end-of-day analytics on the GME listed-options chain.
Every trading day at ~21:00 UTC the universe of listed call/put
contracts is snapshotted from Yahoo Finance's v7 options endpoint, the
underlying close price is read from Yahoo's v8 chart endpoint, and a
fixed set of derived risk metrics — max pain, P/C ratio, IV30, HV20,
net GEX, strike-axis GEX zero-cross, dealer net gamma, IV rank — is
recomputed for that `trading_date`. The mart is the canonical
public-repo example for `mart-forge`; its purpose is to demonstrate the
full lifecycle (source-discovery → BRD → TDD → bootstrap → DQC →
dashboard) end-to-end against a free, publicly-available data source
with external comparators.

Stakeholder list and full business context are in BRD §B-2; the BRD's
"Dealer Assumption" subsection is the single source of truth for the
GEX sign convention (`sign_dealer(call) = −1`, `sign_dealer(put) =
+1`), which propagates verbatim into every formula in this TDD.

---

## T-3: Metrics Breakdown

| metric_name             | metric_definition                                                                                                                                                                                                                                                          | source_type | link_status        | calculation_logic                                                                                                                                                                                                                                                                                                                              | target_table                            |
|-------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|--------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| spot                    | Regular-session close of GME for the `trading_date` the mart used (Yahoo v8 chart bar OHLC close).                                                                                                                                                                          | native      | exact              | `SELECT close FROM gme_dwd_price_eod WHERE trading_date = :d`                                                                                                                                                                                                                                                                                  | `gme_ads_market_dashboard`               |
| max_pain                | Strike minimising aggregate ITM dollar OI for the nearest unexpired weekly expiry, with strikes deduplicated per side before summation. K is the candidate underlying close; K_under is the option strike.                                                                  | derived     | exact              | `argmin_K Σ_calls oi · greatest(0, K − K_under) + Σ_puts oi · greatest(0, K_under − K)` over distinct strikes per side per expiry (K = candidate underlying, K_under = option strike → ITM intrinsic value, not OTM distance; see T-13 `gme_dws_perf_max_pain` for the SQL).                                                                  | `gme_ads_market_dashboard`               |
| pc_ratio_oi             | Σ(put OI) / Σ(call OI) across the full chain on `trading_date`.                                                                                                                                                                                                              | derived     | exact              | `SUM(CASE WHEN option_type='put' THEN open_interest ELSE 0 END) / NULLIF(SUM(CASE WHEN option_type='call' THEN open_interest ELSE 0 END), 0)` against `gme_dwd_options_chain`.                                                                                                                                                                  | `gme_ads_market_dashboard`               |
| iv30                    | OI-weighted ATM implied vol, interpolated to constant 30-cal-day tenor by linear interpolation in total variance (σ²·t), annualised.                                                                                                                                         | derived     | proxy              | Per BRD §B-3 iv30 row: per-expiry ATM-band weighted-mean σ → `v_T = σ_T² · T` → linearly interpolate `v_30` between two bracketing expiries → `iv30 = sqrt(v_30 / (30/365))`. See T-13 `gme_dws_perf_implied_vol`.                                                                                                                              | `gme_ads_market_dashboard`               |
| hv20                    | Annualised stddev of trailing 20 daily log returns of GME close.                                                                                                                                                                                                             | derived     | exact              | `stddev_samp(ln(close / lag(close,1))) over (order by trading_date rows 19 preceding) · sqrt(252)` against `gme_dwd_price_eod`.                                                                                                                                                                                                                  | `gme_ads_market_dashboard`               |
| net_gex                 | Σ over **full chain** of `γ · OI · 100 · spot² · 0.01 · sign_dealer(type)`, USD per 1% spot move.                                                                                                                                                                            | derived     | unsupported        | `SUM(gamma_bs · open_interest · 100 · pow(spot, 2) · 0.01 · sign_dealer)` against `gme_dwd_options_chain_greeks` (scope = all expiries). `gamma_bs` is the Black-Scholes per-share γ at `r=0.045` (see T-13 `gme_dws_perf_dealer_gamma`).                                                                                                       | `gme_ads_market_dashboard`               |
| gex_zero_cross_strike   | Strike at which the running cumulative sum of per-strike GEX (sorted ascending by strike, evaluated at current `spot s₀`, front-month only) changes sign. Strike-axis diagnostic, NOT a spot price.                                                                          | derived     | unsupported        | Algorithm in T-13 `gme_dws_perf_dealer_gamma_front_month` step 4; **deterministic tie-break: crossing nearest current spot; if equidistant, the lower strike** (closes reviewer item C). Returns NULL on no sign change.                                                                                                                         | `gme_ads_market_dashboard`               |
| iv_rank                 | Percentile of current iv30 within trailing 252-trading-day distribution of iv30 (0–100). Chronological rolling: the rank of *today's* iv30 against the *prior* 252 trading days' iv30 distribution.                                                                          | derived     | phase-gated        | Chronological rolling percentile: window ORDERS BY `trading_date` (NOT by `iv30`), and the percentile is the share of prior non-null iv30 observations less than or equal to today's iv30. SQL form in T-13 `gme_dws_perf_implied_vol`. Carries `iv_rank_label` ∈ {provisional, final} and `iv_rank_lookback_days` (rolling count of non-null iv30).                                  | `gme_ads_market_dashboard`               |
| dealer_net_gamma        | Σ over **front-month expiry only** of `γ · OI · 100 · sign_dealer(type)`, shares per 1% spot move.                                                                                                                                                                            | derived     | unsupported        | `SUM(gamma_bs · open_interest · 100 · sign_dealer)` against `gme_dwd_options_chain_greeks WHERE front_expiry_flag = TRUE` (closes Phase B.5 finding E — `front_expiry_flag` from T-11 is the single source of truth for "front"; the round-1 draft referenced an undefined `front_expiry_date` symbol). See T-13 `gme_dws_perf_dealer_gamma_front_month`.                                                                                                                                                              | `gme_ads_market_dashboard`               |

> `iv_rank.link_status` is **phase-gated** as in the BRD: while
> `iv_rank_lookback_days < 252` it is `unsupported` (provisional);
> once `iv_rank_lookback_days >= 252` it flips to `proxy` against
> Market Chameleon's IV-rank page within ±5%. The lifecycle of the
> `link_status_active` field is owned by Phase D `/mart-dqc` per
> reviewer item E (see T-18 `iv_rank_link_status_active_lifecycle`).

---

## T-4: Design Consideration (4-Step Kimball)

### Step 1: Select the Business Process

End-of-day snapshot of the GME options chain and computation of the
nine derived risk metrics in §T-3 for the latest `trading_date`.

### Step 2: Declare the Grain

Two atomic grains are stored:

- `gme_ods_options_chain_snapshot`: one row per
  `(trading_date, expiry_date, strike, option_type)`. This is the
  finest grain in the warehouse — the full Yahoo v7 options-chain
  contract surface for one trading day.
- `gme_ods_price_history`: one row per `trading_date` for the
  underlying close price.

All downstream DWD / DWS / ADS rows aggregate up from one of these
two atomic grains.

### Step 3: Identify the Dimensions

- `dim_date` — calendar dimension (2020-01-01 → 2027-12-31) with
  `is_trading_day` flag, day-of-week, week/month start anchors. Joined
  on `trading_date` and on `expiry_date`.
- `dim_holidays` — US market holidays for the same window.
- `dim_macro_events` — manually curated FOMC + CPI + earnings dates
  for the `dim_date` coverage window.

### Step 4: Identify the Facts

- `gme_dwd_options_chain` — cleaned, deduplicated chain rows with
  `time_to_expiry_years` and pull provenance attached.
- `gme_dwd_options_chain_greeks` — same rows with Black-Scholes γ
  recomputed at `r = 0.045` (per BRD L-4) and `sign_dealer` resolved
  from the locked dealer-assumption map.
- `gme_dwd_price_eod` — cleaned EOD prices with `log_return_1d`.
- `gme_dws_perf_implied_vol` — `iv30`, `hv20`, rolling
  `iv_rank_lookback_days`, `iv_rank`, `iv_rank_label`.
- `gme_dws_perf_max_pain` — one row per `(trading_date, expiry_date)`
  with `max_pain_strike` after per-side strike dedup.
- `gme_dws_perf_dealer_gamma` — chain-wide `net_gex` per
  `trading_date`.
- `gme_dws_perf_dealer_gamma_front_month` — front-month-only
  `dealer_net_gamma` plus `gex_zero_cross_strike` with the
  deterministic tie-break in §T-13.

---

## T-5: Bus Matrix

| Dimension / Fact Table                       | dim_date | dim_holidays | dim_macro_events | gme_dwd_options_chain | gme_dwd_options_chain_greeks | gme_dwd_price_eod |
|----------------------------------------------|----------|--------------|------------------|------------------------|-------------------------------|--------------------|
| EOD chain snapshot                           | X        | X            | X                | X                      | X                             |                    |
| EOD underlying price                         | X        | X            |                  |                        |                               | X                  |
| IV / HV time series                          | X        |              | X                |                        |                               | X                  |
| Max-pain per (trading_date, expiry_date)     | X        |              |                  | X                      |                               |                    |
| Dealer gamma full-chain (net_gex)            | X        |              |                  |                        | X                             | X                  |
| Dealer gamma front-month (dealer_net_gamma)  | X        |              |                  |                        | X                             | X                  |
| `gex_zero_cross_strike`                      | X        |              |                  |                        | X                             | X                  |
| ADS market dashboard                         | X        |              | X                |                        |                               |                    |

---

## T-6: Table Summary

| Layer | Table Name                                | Materialization | Grain                                                          | Description                                                                                                  |
|-------|-------------------------------------------|------------------|----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| ODS   | `gme_ods_options_chain_snapshot`           | incremental      | `(trading_date, expiry_date, strike, option_type)`             | Raw v7 options-chain rows pulled from Yahoo, one HTTP request per expiry per trading day, with provenance.   |
| ODS   | `gme_ods_price_history`                    | incremental      | `(trading_date)`                                               | Raw v8 chart bar OHLC for GME, one row per trading_date, with provenance.                                    |
| DIM   | `dim_date`                                 | table            | `(calendar_date)`                                              | Calendar dimension 2020-01-01 → 2027-12-31, `is_trading_day` flag.                                            |
| DIM   | `dim_holidays`                             | table            | `(holiday_date)`                                               | US market holidays.                                                                                          |
| DIM   | `dim_macro_events`                         | table            | `(event_date, event_type)`                                     | Curated FOMC/CPI/earnings dates within `dim_date` coverage window.                                            |
| DWD   | `gme_dwd_options_chain`                    | table            | `(trading_date, expiry_date, strike, option_type)`             | Cleaned chain rows: dedup, type cast, `time_to_expiry_years`, FK-resolved.                                    |
| DWD   | `gme_dwd_options_chain_greeks`             | table            | `(trading_date, expiry_date, strike, option_type)`             | Chain rows enriched with Black-Scholes γ at `r=0.045` and `sign_dealer` resolved from dealer-assumption map.  |
| DWD   | `gme_dwd_price_eod`                        | table            | `(trading_date)`                                               | Cleaned EOD price with `log_return_1d`.                                                                       |
| DWS   | `gme_dws_perf_implied_vol`                 | table            | `(trading_date)`                                               | `iv30` (linear-in-total-variance interp), `hv20`, rolling `iv_rank`, `iv_rank_label`, `iv_rank_lookback_days`.|
| DWS   | `gme_dws_perf_max_pain`                    | table            | `(trading_date, expiry_date)`                                  | `max_pain_strike` per expiry with per-side strike dedup.                                                       |
| DWS   | `gme_dws_perf_dealer_gamma`                | table            | `(trading_date)`                                               | Full-chain `net_gex` per trading day.                                                                         |
| DWS   | `gme_dws_perf_dealer_gamma_front_month`    | table            | `(trading_date)`                                               | Front-month `dealer_net_gamma` and `gex_zero_cross_strike` with deterministic tie-break.                      |
| ADS   | `gme_ads_market_dashboard`                 | view             | `(trading_date)` — one row per latest available trading_date   | Wide single-row presentation **view** (not table) that backs the Streamlit dashboard, with one column per §T-3 metric, plus freshness fields and per-metric `link_status_active`. Materialised as a view so the `current_date`/`now()`-anchored freshness columns (`most_recent_session_close_ts_utc`, `pull_lag_hours`, `is_stale`) re-evaluate at every dashboard query, not at every `dbt run` (closes reviewer Phase B.5 finding 3). |

---

## T-7: Data Architecture Diagram

```
Yahoo Finance v7 options endpoint  Yahoo Finance v8 chart endpoint   Seed CSVs (dim_date, dim_holidays, dim_macro_events)
            |                                  |                                 |
            v                                  v                                 v
[ ODS gme_ods_options_chain_snapshot ]  [ ODS gme_ods_price_history ]    [ DIM seeds ]
            |                                  |                                 |
            +-------------------+------+-------+------+--------------------------+
                                |             |
                                v             v
                  [ DWD gme_dwd_options_chain ]   [ DWD gme_dwd_price_eod ]
                                |                         |
                                v                         v
                  [ DWD gme_dwd_options_chain_greeks ]    |
                                |                         |
        +-----------------------+-------------------------+---------------------------+
        |                                |                            |               |
        v                                v                            v               v
[ DWS gme_dws_perf_max_pain ] [ DWS gme_dws_perf_dealer_gamma ] [ DWS gme_dws_perf_dealer_gamma_front_month ] [ DWS gme_dws_perf_implied_vol ]
        |                                |                            |               |
        +--------------+-----------------+----------------------------+---------------+
                       v
            [ ADS gme_ads_market_dashboard ]
                       |
                       v
            [ Streamlit dashboard / BI ]
```

Layer rule: each arrow runs strictly downward (ODS → DIM → DWD → DWS →
ADS). No backward references — enforced by `scripts/lint_layer_direction.py`.

---

## T-8: Table Schema Detail

> All schema sections (T-9 through T-14) use the 6-column format below.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|

`calculation` rules:
- Native columns: `pass-through from <provider>.<field>`.
- Derived columns: actual SQL or formula. No prose placeholders.
- Hybrid columns: native reference + derivation formula + tolerance.

---

## T-9: ODS Table Columns

### ODS Contract Table — `gme_ods_options_chain_snapshot`

| Property              | Value                                                                                                                |
|-----------------------|----------------------------------------------------------------------------------------------------------------------|
| source                | yfinance v7 — `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix_expiry_seconds>` per expiry          |
| grain                 | one row per `(trading_date, expiry_date, strike, option_type)`                                                       |
| logical_partition     | `trading_date`                                                                                                       |
| incremental_strategy  | delete+insert                                                                                                        |
| unique_key            | `(trading_date, expiry_date, strike, option_type)`                                                                   |
| backfill              | Backfill is a single-day operation (Yahoo v7 returns current snapshot only). Initial load = today's chain only.       |
| restatement           | Snapshot is immutable; late-arriving corrections from Yahoo (rare) trigger a delete+insert for the affected `trading_date`. |
| provenance_columns    | provider, pull_ts_utc, run_id                                                                                        |

### `gme_ods_options_chain_snapshot` Columns

| column_name        | data_type | definition                                                                                  | example_value      | calculation                                                                                                                                                                                  | data_source                                       |
|--------------------|-----------|---------------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| trading_date       | DATE      | UTC date the snapshot pull was performed (mapped to NYSE session date).                      | 2026-06-02         | pass-through from system                                                                                                                                                                      | system                                            |
| expiry_date        | DATE      | Listed option expiry date.                                                                  | 2026-06-20         | pass-through from yfinance.optionChain.result[0].expirationDates[i]                                                                                                                            | yfinance v7                                       |
| strike             | DOUBLE    | Listed strike price in USD.                                                                  | 25.0               | pass-through from yfinance.optionChain.result[0].options[0].calls[i].strike                                                                                                                    | yfinance v7                                       |
| option_type        | VARCHAR   | 'call' or 'put'.                                                                            | 'call'             | pass-through from yfinance branch (`.calls` or `.puts`)                                                                                                                                       | yfinance v7                                       |
| open_interest      | BIGINT    | Number of contracts outstanding for this (date, expiry, strike, type).                       | 12453              | pass-through from yfinance.optionChain.result[0].options[0].calls[i].openInterest                                                                                                              | yfinance v7                                       |
| implied_volatility | DOUBLE    | Yahoo's published IV as an annualised decimal fraction.                                      | 0.78               | pass-through from yfinance.optionChain.result[0].options[0].calls[i].impliedVolatility                                                                                                         | yfinance v7                                       |
| last_price         | DOUBLE    | Last trade price for this contract (USD).                                                    | 2.34               | pass-through from yfinance.optionChain.result[0].options[0].calls[i].lastPrice                                                                                                                 | yfinance v7                                       |
| provider           | VARCHAR   | Name of the upstream provider.                                                              | 'yfinance'         | pass-through from system                                                                                                                                                                      | system                                            |
| pull_ts_utc        | TIMESTAMP | UTC timestamp of the HTTP fetch.                                                            | 2026-06-02 21:05:12 | pass-through from system                                                                                                                                                                      | system                                            |
| run_id             | VARCHAR   | Unique identifier for the ETL run.                                                          | 'run_20260602_2105' | pass-through from system                                                                                                                                                                      | system                                            |

### ODS Contract Table — `gme_ods_price_history`

| Property              | Value                                                                                                                |
|-----------------------|----------------------------------------------------------------------------------------------------------------------|
| source                | yfinance v8 — `https://query2.finance.yahoo.com/v8/finance/chart/GME?interval=1d&range=2mo`                            |
| grain                 | one row per `trading_date`                                                                                           |
| logical_partition     | `trading_date`                                                                                                       |
| incremental_strategy  | delete+insert                                                                                                        |
| unique_key            | `trading_date`                                                                                                       |
| backfill              | First load fetches `range=5y`; steady-state fetches `range=2mo` (covers hv20 + 2-week buffer).                        |
| restatement           | Yahoo may publish corrections; treat as delete+insert keyed on `trading_date`.                                       |
| provenance_columns    | provider, pull_ts_utc, run_id                                                                                        |

### `gme_ods_price_history` Columns

| column_name  | data_type | definition                                                                | example_value      | calculation                                                                                                                                       | data_source                                |
|--------------|-----------|---------------------------------------------------------------------------|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| trading_date | DATE      | NYSE session date corresponding to the bar.                                | 2026-06-02         | pass-through from yfinance.chart.result[0].timestamp[i] (mapped to NYSE date)                                                                       | yfinance v8                                |
| open_px      | DOUBLE    | Regular-session open price (USD).                                          | 24.50              | pass-through from yfinance.chart.result[0].indicators.quote[0].open[i]                                                                              | yfinance v8                                |
| high_px      | DOUBLE    | Regular-session high price (USD).                                          | 25.20              | pass-through from yfinance.chart.result[0].indicators.quote[0].high[i]                                                                              | yfinance v8                                |
| low_px       | DOUBLE    | Regular-session low price (USD).                                           | 24.10              | pass-through from yfinance.chart.result[0].indicators.quote[0].low[i]                                                                               | yfinance v8                                |
| close_px     | DOUBLE    | Regular-session close price (USD). Used as `spot` for the trading_date.    | 24.85              | pass-through from yfinance.chart.result[0].indicators.quote[0].close[i]                                                                             | yfinance v8                                |
| volume       | BIGINT    | Regular-session share volume.                                              | 8120433            | pass-through from yfinance.chart.result[0].indicators.quote[0].volume[i]                                                                            | yfinance v8                                |
| provider     | VARCHAR   | Name of the upstream provider.                                            | 'yfinance'         | pass-through from system                                                                                                                            | system                                     |
| pull_ts_utc  | TIMESTAMP | UTC timestamp of the HTTP fetch.                                          | 2026-06-02 21:05:14 | pass-through from system                                                                                                                            | system                                     |
| run_id       | VARCHAR   | Unique identifier for the ETL run.                                        | 'run_20260602_2105' | pass-through from system                                                                                                                            | system                                     |

---

## T-10: DIM Table Columns

### `dim_date` Columns

| column_name      | data_type | definition                                                       | example_value | calculation                                                            | data_source                                  |
|------------------|-----------|------------------------------------------------------------------|---------------|------------------------------------------------------------------------|----------------------------------------------|
| date_sk          | INTEGER   | Surrogate key.                                                   | 20260602      | `cast(strftime(calendar_date, '%Y%m%d') as integer)`                    | generated                                    |
| calendar_date    | DATE      | Calendar date covering 2020-01-01 → 2027-12-31.                  | 2026-06-02    | pass-through from seed CSV `calendar_date`                              | seed CSV                                     |
| is_trading_day   | BOOLEAN   | True if the date is an NYSE regular-session trading day.          | TRUE          | `pandas_market_calendars XNYS schedule(start, end).index.contains(date)` (pre-computed in seed) | seed CSV (generated)               |
| day_of_week      | INTEGER   | ISO day of week (1=Mon, 7=Sun).                                  | 2             | `extract('isodow' from calendar_date)`                                  | derived                                      |
| week_start       | DATE      | First Monday on or before `calendar_date`.                       | 2026-06-01    | `date_trunc('week', calendar_date)`                                     | derived                                      |
| month_start      | DATE      | First day of the month containing `calendar_date`.               | 2026-06-01    | `date_trunc('month', calendar_date)`                                    | derived                                      |

### `dim_holidays` Columns

| column_name   | data_type | definition                                       | example_value | calculation                                                        | data_source                       |
|---------------|-----------|--------------------------------------------------|---------------|--------------------------------------------------------------------|-----------------------------------|
| holiday_sk    | INTEGER   | Surrogate key.                                   | 20260629      | `cast(strftime(holiday_date, '%Y%m%d') as integer)`                 | generated                         |
| holiday_date  | DATE      | NYSE market holiday date.                        | 2026-06-29    | pass-through from seed CSV `holiday_date`                           | seed CSV (pandas_market_calendars)|
| holiday_name  | VARCHAR   | Holiday label (e.g. 'Independence Day').         | 'Memorial Day'| pass-through from seed CSV `holiday_name`                           | seed CSV                          |

### `dim_macro_events` Columns

| column_name     | data_type | definition                                                | example_value          | calculation                                                       | data_source                       |
|-----------------|-----------|-----------------------------------------------------------|------------------------|-------------------------------------------------------------------|-----------------------------------|
| event_sk        | INTEGER   | Surrogate key.                                            | 202606170              | `row_number() over (order by event_date, event_type)`              | generated                         |
| event_date      | DATE      | Date of the event.                                        | 2026-06-17             | pass-through from seed CSV `event_date`                            | seed CSV (manually curated)       |
| event_type      | VARCHAR   | Event class ('FOMC', 'CPI', 'EARNINGS').                  | 'FOMC'                 | pass-through from seed CSV `event_type`                            | seed CSV                          |
| event_label     | VARCHAR   | Human-readable label.                                     | 'FOMC June statement'  | pass-through from seed CSV `event_label`                           | seed CSV                          |

---

## T-11: DWD Table Columns

### `gme_dwd_options_chain` Columns

| column_name             | data_type | definition                                                                                | example_value      | calculation                                                                                                                                                                            | data_source                                  |
|-------------------------|-----------|-------------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| trading_date            | DATE      | NYSE session date of the snapshot.                                                        | 2026-06-02         | pass-through from `gme_ods_options_chain_snapshot.trading_date`                                                                                                                          | ods                                          |
| expiry_date             | DATE      | Listed option expiry date.                                                                | 2026-06-20         | pass-through from `gme_ods_options_chain_snapshot.expiry_date`                                                                                                                            | ods                                          |
| strike                  | DOUBLE    | Listed strike price (USD).                                                                | 25.0               | pass-through from `gme_ods_options_chain_snapshot.strike`                                                                                                                                 | ods                                          |
| option_type             | VARCHAR   | 'call' or 'put'.                                                                          | 'call'             | pass-through from `gme_ods_options_chain_snapshot.option_type`                                                                                                                            | ods                                          |
| open_interest           | BIGINT    | Non-negative OI; rows with NULL or negative OI are dropped.                                | 12453              | `coalesce(open_interest, 0)` with rows `WHERE open_interest IS NOT NULL AND open_interest >= 0`                                                                                          | ods                                          |
| implied_volatility      | DOUBLE    | IV from Yahoo, retained only when `> 0` (Yahoo emits 1e-5 sentinels otherwise).            | 0.78               | `CASE WHEN implied_volatility > 1e-4 THEN implied_volatility ELSE NULL END`                                                                                                              | ods                                          |
| time_to_expiry_years    | DOUBLE    | Year fraction from `trading_date` to `expiry_date` (Act/365).                              | 0.0493             | `(expiry_date - trading_date) / 365.0`                                                                                                                                                    | derived                                      |
| date_sk                 | INTEGER   | FK → `dim_date.date_sk` for the `trading_date`.                                            | 20260602           | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                       | derived                                      |
| expiry_date_sk          | INTEGER   | FK → `dim_date.date_sk` for the `expiry_date`.                                             | 20260620           | `cast(strftime(expiry_date, '%Y%m%d') as integer)`                                                                                                                                        | derived                                      |
| front_expiry_flag       | BOOLEAN   | True iff `expiry_date` is the smallest expiry STRICTLY AFTER `trading_date` for that trading_date — i.e., the nearest *unexpired* expiry. Same-day expiry contracts are excluded so weekly-expiration-day metrics aren't computed on an expiring chain (closes Phase B.5 finding 4 — single source of truth for "front" across `dealer_net_gamma`, `gex_zero_cross_strike`, and `max_pain_strike_front`). | TRUE               | Two-step CTE (DuckDB does not allow FILTER inside window functions): `WITH unexpired AS (SELECT trading_date, expiry_date FROM gme_dwd_options_chain WHERE expiry_date > trading_date), front AS (SELECT trading_date, MIN(expiry_date) AS front_expiry_date FROM unexpired GROUP BY 1) SELECT ..., (expiry_date = front.front_expiry_date AND expiry_date > trading_date) AS front_expiry_flag FROM gme_dwd_options_chain LEFT JOIN front USING (trading_date)`.                                                                                                                                          | derived                                      |
| provider                | VARCHAR   | Provenance.                                                                               | 'yfinance'         | pass-through from `gme_ods_options_chain_snapshot.provider`                                                                                                                               | ods                                          |
| pull_ts_utc             | TIMESTAMP | Provenance.                                                                                | 2026-06-02 21:05:12 | pass-through from `gme_ods_options_chain_snapshot.pull_ts_utc`                                                                                                                            | ods                                          |
| run_id                  | VARCHAR   | Provenance.                                                                                | 'run_20260602_2105' | pass-through from `gme_ods_options_chain_snapshot.run_id`                                                                                                                                 | ods                                          |

### `gme_dwd_options_chain_greeks` Columns

| column_name        | data_type | definition                                                                                            | example_value | calculation                                                                                                                                                                                                                                                                                                                                                                                                                                            | data_source                                       |
|--------------------|-----------|-------------------------------------------------------------------------------------------------------|---------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| trading_date       | DATE      | FK to `gme_dwd_price_eod.trading_date` and `gme_dwd_options_chain.trading_date`.                       | 2026-06-02    | pass-through from `gme_dwd_options_chain.trading_date`                                                                                                                                                                                                                                                                                                                                                                                                  | dwd                                               |
| expiry_date        | DATE      | Same as chain.                                                                                         | 2026-06-20    | pass-through from `gme_dwd_options_chain.expiry_date`                                                                                                                                                                                                                                                                                                                                                                                                   | dwd                                               |
| strike             | DOUBLE    | Strike price.                                                                                          | 25.0          | pass-through from `gme_dwd_options_chain.strike`                                                                                                                                                                                                                                                                                                                                                                                                        | dwd                                               |
| option_type        | VARCHAR   | 'call' or 'put'.                                                                                       | 'call'        | pass-through from `gme_dwd_options_chain.option_type`                                                                                                                                                                                                                                                                                                                                                                                                   | dwd                                               |
| open_interest      | BIGINT    | OI carried for downstream sums.                                                                         | 12453         | pass-through from `gme_dwd_options_chain.open_interest`                                                                                                                                                                                                                                                                                                                                                                                                 | dwd                                               |
| sigma              | DOUBLE    | IV used for γ recomputation.                                                                            | 0.78          | pass-through from `gme_dwd_options_chain.implied_volatility`                                                                                                                                                                                                                                                                                                                                                                                            | dwd                                               |
| spot               | DOUBLE    | Underlying close for the trading_date.                                                                  | 24.85         | `(SELECT close_px FROM gme_dwd_price_eod p WHERE p.trading_date = gme_dwd_options_chain_greeks.trading_date)`                                                                                                                                                                                                                                                                                                                                            | dwd                                               |
| risk_free_rate     | DOUBLE    | Risk-free rate used for γ. Hard-coded per BRD L-4 until Phase D Fred ingest lands.                      | 0.045         | `0.045::double`                                                                                                                                                                                                                                                                                                                                                                                                                                          | constant (BRD L-4)                                |
| gamma_bs           | DOUBLE    | Black-Scholes per-share γ. Equal for call and put at the same (K, T, σ).                                | 0.072         | `exp(- pow(d1, 2) / 2) / (sigma * spot * sqrt(2 * pi() * time_to_expiry_years))` where `d1 = (ln(spot/strike) + (risk_free_rate + 0.5 * pow(sigma, 2)) * time_to_expiry_years) / (sigma * sqrt(time_to_expiry_years))`. Returns NULL when `sigma IS NULL` or `time_to_expiry_years <= 0`.                                                                                                                                                                  | derived                                           |
| sign_dealer        | INTEGER   | Resolved from dealer-assumption map: -1 for calls, +1 for puts.                                          | -1            | `CASE option_type WHEN 'call' THEN -1 WHEN 'put' THEN 1 END`                                                                                                                                                                                                                                                                                                                                                                                              | derived (BRD §B-2 Dealer Assumption)              |
| front_expiry_flag  | BOOLEAN   | Pass-through from `gme_dwd_options_chain.front_expiry_flag`.                                            | TRUE          | pass-through from `gme_dwd_options_chain.front_expiry_flag`                                                                                                                                                                                                                                                                                                                                                                                              | dwd                                               |
| date_sk            | INTEGER   | FK → `dim_date.date_sk`.                                                                                | 20260602      | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                                                                                                                                                                                                                                                                                       | derived                                           |
| pull_ts_utc        | TIMESTAMP | Provenance.                                                                                              | 2026-06-02 21:05:12 | pass-through from `gme_dwd_options_chain.pull_ts_utc`                                                                                                                                                                                                                                                                                                                                                                                                       | dwd                                               |

### `gme_dwd_price_eod` Columns

| column_name     | data_type | definition                                                       | example_value | calculation                                                                                                                | data_source                  |
|-----------------|-----------|------------------------------------------------------------------|---------------|----------------------------------------------------------------------------------------------------------------------------|------------------------------|
| trading_date    | DATE      | NYSE session date.                                               | 2026-06-02    | pass-through from `gme_ods_price_history.trading_date`                                                                      | ods                          |
| open_px         | DOUBLE    | Regular-session open price.                                       | 24.50         | pass-through from `gme_ods_price_history.open_px`                                                                            | ods                          |
| high_px         | DOUBLE    | Regular-session high price.                                       | 25.20         | pass-through from `gme_ods_price_history.high_px`                                                                            | ods                          |
| low_px          | DOUBLE    | Regular-session low price.                                        | 24.10         | pass-through from `gme_ods_price_history.low_px`                                                                             | ods                          |
| close_px        | DOUBLE    | Regular-session close. The `spot` used by every downstream metric.| 24.85         | pass-through from `gme_ods_price_history.close_px`                                                                            | ods                          |
| volume          | BIGINT    | Regular-session share volume.                                      | 8120433       | pass-through from `gme_ods_price_history.volume`                                                                              | ods                          |
| log_return_1d   | DOUBLE    | Trailing 1-day log return; NULL for the first row.                | 0.0141        | `ln(close_px / lag(close_px, 1) over (order by trading_date))`                                                                | derived                      |
| date_sk         | INTEGER   | FK → `dim_date.date_sk`.                                          | 20260602      | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                            | derived                      |
| provider        | VARCHAR   | Provenance.                                                       | 'yfinance'    | pass-through from `gme_ods_price_history.provider`                                                                            | ods                          |
| pull_ts_utc     | TIMESTAMP | Provenance.                                                       | 2026-06-02 21:05:14 | pass-through from `gme_ods_price_history.pull_ts_utc`                                                                          | ods                          |

---

## T-12: Count DWS Table Columns

> No counting DWS table is required by this mart — every published metric
> is either a sum, a ratio, a percentile, an aggregation in dollars, or a
> root-find. The "count" layer is retained in the spec only for layer
> rule conformance; instantiated tables live under T-13 Performance DWS.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
| _none_      | _n/a_     | _n/a_      | _n/a_         | `(no table)` | _n/a_       |

---

## T-13: Performance DWS Table Columns

### `gme_dws_perf_max_pain` Columns — grain `(trading_date, expiry_date)`

| column_name        | data_type | definition                                                                              | example_value | calculation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | data_source                          |
|--------------------|-----------|-----------------------------------------------------------------------------------------|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| trading_date       | DATE      | Session date.                                                                            | 2026-06-02    | pass-through from `gme_dwd_options_chain.trading_date`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | dwd                                  |
| expiry_date        | DATE      | Listed expiry.                                                                           | 2026-06-20    | pass-through from `gme_dwd_options_chain.expiry_date`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | dwd                                  |
| n_distinct_strikes | INTEGER   | Distinct strike count for this expiry (per side dedup already done).                      | 47            | `count(distinct strike)` after per-side dedup CTE (see calculation column for max_pain_strike)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | derived                              |
| max_pain_strike    | DOUBLE    | Strike minimising aggregate ITM dollar OI for this (date, expiry). Per-side dedup first. K is the candidate underlying close; K_under is the option strike. | 24.0          | Two-CTE form: (1) `WITH dedup AS (SELECT trading_date, expiry_date, strike, option_type, sum(open_interest) AS oi FROM gme_dwd_options_chain GROUP BY 1,2,3,4)`; (2) for each candidate underlying close `K` in the distinct strike universe at `(trading_date, expiry_date)`, compute the aggregate ITM intrinsic value `pain(K) = SUM_calls(oi * GREATEST(0, K - K_under)) + SUM_puts(oi * GREATEST(0, K_under - K))` where `K_under` iterates over the same distinct strike universe (calls go ITM when `K > K_under`; puts go ITM when `K < K_under` — closes reviewer Phase B.5 finding 1, where the round-1 draft had the terms swapped and was computing OTM distance, not ITM dollar pain); (3) `argmin_K pain(K)`. CRITICAL: per-side strike dedup BEFORE the cross join with the candidate-strike universe, otherwise the cardinality bug from predecessor `bae4af2` returns. Asymmetric-fixture singular test `max_pain_fixture_asymmetric_chain.sql` (1,000 calls @ K_under=20, 1,000 puts @ K_under=30) asserts `max_pain_strike ∈ [20, 30]` — would FAIL under the swapped terms (those would tie at strikes 20/25/30 with pain=0, picking 20). | derived                              |
| date_sk            | INTEGER   | FK → `dim_date.date_sk` (`trading_date`).                                                 | 20260602      | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | derived                              |
| expiry_date_sk     | INTEGER   | FK → `dim_date.date_sk` (`expiry_date`).                                                  | 20260620      | `cast(strftime(expiry_date, '%Y%m%d') as integer)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | derived                              |

### `gme_dws_perf_implied_vol` Columns — grain `(trading_date)`

| column_name              | data_type | definition                                                                                                                  | example_value | calculation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | data_source                                |
|--------------------------|-----------|-----------------------------------------------------------------------------------------------------------------------------|---------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|
| trading_date             | DATE      | Session date.                                                                                                                | 2026-06-02    | pass-through from `gme_dwd_options_chain.trading_date`                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | dwd                                        |
| iv30                     | DOUBLE    | Linear-in-total-variance interpolation of OI-weighted ATM IV to a constant 30-cal-day tenor, annualised decimal.              | 0.85          | Step 1 (NULL-safe per Phase B.5 finding 5 — numerator and denominator must see the same rowset; the Yahoo `1e-5` sentinel is mapped to NULL in DWD line 299): per expiry, restrict to ATM-band rows with non-NULL `sigma` via the FROM clause, then `iv_atm = SUM(oi · sigma) / NULLIF(SUM(oi), 0)`. Equivalent explicit form: `SUM(oi · sigma) / NULLIF(SUM(CASE WHEN sigma IS NOT NULL THEN oi ELSE 0 END), 0)` over the ATM band `|strike/spot − 1| ≤ 0.05` across both call+put rows. This prevents the round-1 bias where the denominator double-counted OI from NULL-IV rows and the resulting weighted mean was systematically biased downward. Step 2: identify the two bracketing expiries `(T_near, T_far)` with `T_near ≤ 30/365 < T_far`. Step 3: `v_T = pow(iv_atm_T, 2) · T_T`; Step 4: `v_30 = v_near + (v_far − v_near) · ((30/365 − T_near) / (T_far − T_near))`. Step 5: `iv30 = sqrt(v_30 / (30/365))`. If only one expiry exists with `T ≥ 30/365`, return its `iv_atm` directly. If no expiry, NULL. (BRD §B-3 iv30 row.)               | derived                                    |
| hv20                     | DOUBLE    | Annualised stddev of trailing 20 daily log returns.                                                                          | 0.92          | `stddev_samp(log_return_1d) over (order by trading_date rows 19 preceding) · sqrt(252)`                                                                                                                                                                                                                                                                                                                                                                                                                                       | dwd                                        |
| iv_rank_lookback_days    | INTEGER   | Rolling count of non-null `iv30` observations in the trailing 252 trading days.                                              | 134           | `count(iv30) over (order by trading_date rows 251 preceding)` against `gme_dws_perf_implied_vol` (the model self-references its own prior-day rows via dbt ref + `is_incremental()` guard).                                                                                                                                                                                                                                                                                                                                   | derived                                    |
| iv_rank                  | DOUBLE    | Percentile (0–100) of current `iv30` within the trailing 252 non-null `iv30` values, ranked chronologically. NULL while `iv_rank_lookback_days < 252`. | 67.2          | Chronological rolling percentile (closes reviewer Phase B.5 finding 2). Implemented via a self-join against the trailing 252-trading-day slice: `WITH base AS (SELECT trading_date, iv30 FROM {{ ref('gme_dws_perf_implied_vol') }} WHERE iv30 IS NOT NULL), counted AS (SELECT b1.trading_date, b1.iv30, count(*) FILTER (WHERE b2.iv30 <= b1.iv30 AND b2.trading_date < b1.trading_date) AS rank_count, count(*) FILTER (WHERE b2.trading_date < b1.trading_date) AS denom FROM base b1 LEFT JOIN base b2 ON b2.trading_date BETWEEN b1.trading_date - INTERVAL '500 days' AND b1.trading_date - INTERVAL '1 day' AND b2.iv30 IS NOT NULL GROUP BY 1,2) SELECT trading_date, CASE WHEN iv_rank_lookback_days >= 252 THEN 100.0 * rank_count / NULLIF(denom, 0) ELSE NULL END AS iv_rank FROM counted JOIN ... USING (trading_date)`. Window ORDERs BY `trading_date`, percentile counts *prior* iv30 values ≤ current. NOT `percent_rank() OVER (ORDER BY iv30)` — that ordering is by magnitude, not time, and produces a degenerate measure of the current row's position within its own iv30-sorted frame. | derived                                    |
| iv_rank_label            | VARCHAR   | 'provisional' until 252 non-null observations accumulate, then 'final'.                                                       | 'provisional' | `CASE WHEN iv_rank_lookback_days >= 252 THEN 'final' ELSE 'provisional' END`                                                                                                                                                                                                                                                                                                                                                                                                                                                  | derived                                    |
| date_sk                  | INTEGER   | FK → `dim_date.date_sk`.                                                                                                     | 20260602      | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | derived                                    |

### `gme_dws_perf_dealer_gamma` Columns — grain `(trading_date)`, **scope = full chain**

| column_name   | data_type | definition                                                                                                                                                          | example_value      | calculation                                                                                                                                                                                                                                                  | data_source                                  |
|---------------|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| trading_date  | DATE      | Session date.                                                                                                                                                       | 2026-06-02         | pass-through from `gme_dwd_options_chain_greeks.trading_date`                                                                                                                                                                                                  | dwd                                          |
| net_gex       | DOUBLE    | Full-chain dealer net GEX in USD per 1% spot move (negative = dealers net short gamma).                                                                              | -132450000.0       | `SUM(gamma_bs · open_interest · 100 · pow(spot, 2) · 0.01 · sign_dealer)` over **all rows** of `gme_dwd_options_chain_greeks` for `trading_date`.                                                                                                                | dwd                                          |
| n_rows_used   | INTEGER   | Count of `(expiry, strike, type)` rows summed; provenance for T3.4.                                                                                                  | 2418               | `count(*)`                                                                                                                                                                                                                                                     | derived                                      |
| scope_label   | VARCHAR   | Literal 'full_chain'. Provenance assertion for T3.4 distinction check.                                                                                               | 'full_chain'       | `'full_chain'::varchar`                                                                                                                                                                                                                                        | constant                                     |
| date_sk       | INTEGER   | FK → `dim_date.date_sk`.                                                                                                                                            | 20260602           | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                                                                                            | derived                                      |

### `gme_dws_perf_dealer_gamma_front_month` Columns — grain `(trading_date)`, **scope = front-month only**

| column_name              | data_type | definition                                                                                                                                                                       | example_value      | calculation                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | data_source                                  |
|--------------------------|-----------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| trading_date             | DATE      | Session date.                                                                                                                                                                    | 2026-06-02         | pass-through from `gme_dwd_options_chain_greeks.trading_date`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | dwd                                          |
| dealer_net_gamma         | DOUBLE    | Front-month dealer net gamma in **shares per 1% spot move** (no `spot² · 0.01` factor).                                                                                            | -218450.0          | `SUM(gamma_bs · open_interest · 100 · sign_dealer)` over `gme_dwd_options_chain_greeks WHERE front_expiry_flag = TRUE AND trading_date = :d`.                                                                                                                                                                                                                                                                                                                                                                                                                                          | dwd                                          |
| n_rows_used              | INTEGER   | Count of `(strike, type)` rows summed; provenance for T3.4 — must be < `gme_dws_perf_dealer_gamma.n_rows_used` whenever back-month expiries carry OI.                              | 184                | `count(*)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | derived                                      |
| scope_label              | VARCHAR   | Literal 'front_month_only'. Provenance assertion for T3.4 distinction check.                                                                                                      | 'front_month_only' | `'front_month_only'::varchar`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | constant                                     |
| gex_zero_cross_strike    | DOUBLE    | Strike at which running cumulative `per_strike_gex_at_s0` (front-month only, sorted ascending by strike) changes sign; linearly interpolated. Deterministic tie-break: crossing nearest current `spot`; on equidistant ties, the **lower** strike (closes reviewer item C). NULL on no sign change. | 22.50              | Step 1: `per_strike_gex = SUM(gamma_bs · open_interest · 100 · pow(spot,2) · 0.01 · sign_dealer) group by strike` for the front month at trading_date. Step 2: sort by `strike asc`. Step 3: running cumulative `cum_gex = sum(per_strike_gex) over (order by strike rows unbounded preceding)`. Step 4: find every adjacent pair `(K_below, K_above)` where `sign(cum_gex_below) ≠ sign(cum_gex_above)` (counting an exact-zero `cum_gex_above` as the sign of the next non-zero entry — i.e., the zero is treated as already having crossed when the algorithm walks past it). Step 5: for each candidate adjacent pair, the interpolated crossing strike is `K* = K_below - cum_gex_below · (K_above − K_below) / (cum_gex_above − cum_gex_below)`, **with the explicit exact-zero substitution rule (closes Phase B.5 finding D): if `cum_gex_above` is exactly zero, the running sum hits zero at `K_above` itself and there is no need to interpolate — set `K* = K_above` (do NOT divide by `cum_gex_above − cum_gex_below` because that ratio degenerates to `cum_gex_below / cum_gex_below = 1` and gives `K* = K_below`, which would lie one step shy of the actual zero). Symmetrically, if `cum_gex_below` is exactly zero, set `K* = K_below`. Only when both endpoints are strictly non-zero do we apply the linear-interpolation formula.** Step 6: if multiple `K*` exist, pick the one with the smallest `abs(K* − spot)`; on equidistant ties, the lower strike. Step 7: NULL if no sign change. | derived                                      |
| gex_zero_cross_n_candidates | INTEGER | Count of candidate crossings the algorithm found before applying the nearest-spot tie-break. ≥2 indicates a multi-crossing day. | 1                | `count(*)` over the candidate set from step 4.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | derived                                      |
| date_sk                  | INTEGER   | FK → `dim_date.date_sk`.                                                                                                                                                          | 20260602           | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | derived                                      |

---

## T-14: ADS / Presentation Table Columns

### `gme_ads_market_dashboard` Columns — grain `(trading_date)`

| column_name                       | data_type | definition                                                                                                            | example_value         | calculation                                                                                                                                                                       | data_source                                  |
|-----------------------------------|-----------|-----------------------------------------------------------------------------------------------------------------------|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| trading_date                      | DATE      | Most recent trading_date present in both `gme_dwd_price_eod` and `gme_dwd_options_chain`.                              | 2026-06-02            | `SELECT MAX(p.trading_date) FROM gme_dwd_price_eod p INNER JOIN (SELECT DISTINCT trading_date FROM gme_dwd_options_chain) c ON p.trading_date = c.trading_date`                    | dwd                                          |
| spot                              | DOUBLE    | Underlying close used by every metric.                                                                                | 24.85                 | `(SELECT close_px FROM gme_dwd_price_eod WHERE trading_date = ads.trading_date)`                                                                                                  | dwd                                          |
| max_pain_strike_front             | DOUBLE    | Front-expiry `max_pain_strike` for the dashboard tile. "Front" follows the single definition in T-11 `front_expiry_flag` — nearest expiry strictly after `trading_date` — so all "front" tiles in the dashboard target the same expiry on weekly-expiration days (closes Phase B.5 finding 4). | 24.0                  | `(SELECT mp.max_pain_strike FROM gme_dws_perf_max_pain mp INNER JOIN (SELECT DISTINCT trading_date, expiry_date FROM gme_dwd_options_chain_greeks WHERE front_expiry_flag = TRUE) fe ON mp.trading_date = fe.trading_date AND mp.expiry_date = fe.expiry_date WHERE mp.trading_date = ads.trading_date)` | dws                                          |
| pc_ratio_oi                       | DOUBLE    | Chain-wide put/call OI ratio.                                                                                          | 0.62                  | `SUM(CASE WHEN option_type='put' THEN open_interest ELSE 0 END) / NULLIF(SUM(CASE WHEN option_type='call' THEN open_interest ELSE 0 END), 0)` against `gme_dwd_options_chain WHERE trading_date = ads.trading_date` | dwd                                          |
| iv30                              | DOUBLE    | Constant-maturity ATM IV.                                                                                              | 0.85                  | `(SELECT iv30 FROM gme_dws_perf_implied_vol WHERE trading_date = ads.trading_date)`                                                                                               | dws                                          |
| hv20                              | DOUBLE    | Realised vol.                                                                                                          | 0.92                  | `(SELECT hv20 FROM gme_dws_perf_implied_vol WHERE trading_date = ads.trading_date)`                                                                                               | dws                                          |
| net_gex                           | DOUBLE    | Full-chain net GEX in USD per 1%.                                                                                      | -132450000.0          | `(SELECT net_gex FROM gme_dws_perf_dealer_gamma WHERE trading_date = ads.trading_date)`                                                                                            | dws                                          |
| gex_zero_cross_strike             | DOUBLE    | Front-month strike-axis GEX zero cross.                                                                                | 22.50                 | `(SELECT gex_zero_cross_strike FROM gme_dws_perf_dealer_gamma_front_month WHERE trading_date = ads.trading_date)`                                                                  | dws                                          |
| dealer_net_gamma                  | DOUBLE    | Front-month dealer net gamma in shares per 1%.                                                                          | -218450.0             | `(SELECT dealer_net_gamma FROM gme_dws_perf_dealer_gamma_front_month WHERE trading_date = ads.trading_date)`                                                                       | dws                                          |
| iv_rank                           | DOUBLE    | Percentile of `iv30` within trailing 252 sessions.                                                                      | 67.2                  | `(SELECT iv_rank FROM gme_dws_perf_implied_vol WHERE trading_date = ads.trading_date)`                                                                                             | dws                                          |
| iv_rank_label                     | VARCHAR   | 'provisional' or 'final' (drives badge color).                                                                          | 'provisional'         | `(SELECT iv_rank_label FROM gme_dws_perf_implied_vol WHERE trading_date = ads.trading_date)`                                                                                       | dws                                          |
| iv_rank_lookback_days             | INTEGER   | Rolling count of non-null `iv30` (drives Phase D lifecycle flip — see T-18).                                            | 134                   | `(SELECT iv_rank_lookback_days FROM gme_dws_perf_implied_vol WHERE trading_date = ads.trading_date)`                                                                               | dws                                          |
| iv_rank_link_status_active        | VARCHAR   | Phase-gated link status: 'unsupported' while `iv_rank_lookback_days < 252`, else 'proxy'.                                | 'unsupported'         | `CASE WHEN iv_rank_lookback_days >= 252 THEN 'proxy' ELSE 'unsupported' END`                                                                                                       | derived                                      |
| last_pull_ts_utc                  | TIMESTAMP | Max `pull_ts_utc` across both ODS tables for the trading_date.                                                          | 2026-06-02 21:05:14   | `GREATEST((SELECT MAX(pull_ts_utc) FROM gme_ods_options_chain_snapshot WHERE trading_date = ads.trading_date), (SELECT MAX(pull_ts_utc) FROM gme_ods_price_history WHERE trading_date = ads.trading_date))` | ods                                          |
| most_recent_session_close_ts_utc  | TIMESTAMP | 21:00 UTC on the latest `dim_date.calendar_date` with `is_trading_day=TRUE` that is `<= current_date`. Recomputed at every dashboard query because the ADS is materialised as a view (closes Phase B.5 finding 3). | 2026-06-02 21:00:00   | `(SELECT MAX(calendar_date) FROM dim_date WHERE is_trading_day = TRUE AND calendar_date <= current_date) + INTERVAL '21 hours'`                                                    | dim (view; query-time)                       |
| pull_lag_hours                    | DOUBLE    | Signed hours: `(last_pull_ts_utc - most_recent_session_close_ts_utc) / 1h`. Drives T2.1/T2.3 banner. Recomputed at every dashboard query (view materialisation; closes Phase B.5 finding 3). | 0.09                  | `extract(epoch from (last_pull_ts_utc - most_recent_session_close_ts_utc)) / 3600.0`                                                                                                | derived (view; query-time)                   |
| is_stale                          | BOOLEAN   | TRUE iff T2.1 inequality is false (drives STALE banner per BRD L-7 round-2-itemA wording). Recomputed at every dashboard query — Monday-morning queries against an unrefreshed materialisation now correctly fire STALE because `most_recent_session_close_ts_utc` re-evaluates to Friday or Monday's close depending on wall clock (closes Phase B.5 finding 3). | FALSE                 | `NOT (pull_lag_hours >= 0 AND pull_lag_hours <= 26)`                                                                                                                                | derived (view; query-time)                   |
| date_sk                           | INTEGER   | FK → `dim_date.date_sk`.                                                                                                | 20260602              | `cast(strftime(trading_date, '%Y%m%d') as integer)`                                                                                                                                  | derived                                      |

---

## T-15: Physical Design

### Materialization Strategy

| Table                                            | Materialization | Partition Key   | Cluster Key                  |
|--------------------------------------------------|------------------|-----------------|------------------------------|
| `gme_ods_options_chain_snapshot`                  | incremental      | `trading_date`  | `(expiry_date, option_type)` |
| `gme_ods_price_history`                           | incremental      | `trading_date`  | --                           |
| `dim_date`                                        | table            | --              | --                           |
| `dim_holidays`                                    | table            | --              | --                           |
| `dim_macro_events`                                | table            | --              | `(event_type)`               |
| `gme_dwd_options_chain`                           | table            | --              | `(trading_date, expiry_date)`|
| `gme_dwd_options_chain_greeks`                    | table            | --              | `(trading_date, expiry_date)`|
| `gme_dwd_price_eod`                               | table            | --              | `(trading_date)`             |
| `gme_dws_perf_max_pain`                           | table            | --              | `(trading_date, expiry_date)`|
| `gme_dws_perf_implied_vol`                        | table            | --              | `(trading_date)`             |
| `gme_dws_perf_dealer_gamma`                       | table            | --              | `(trading_date)`             |
| `gme_dws_perf_dealer_gamma_front_month`           | table            | --              | `(trading_date)`             |
| `gme_ads_market_dashboard`                        | view             | --              | --                           |

### Storage Estimates

| Table                                            | Initial load                                  | Steady-state daily increment                |
|--------------------------------------------------|-----------------------------------------------|---------------------------------------------|
| `gme_ods_options_chain_snapshot`                  | ~2,500 rows × 1 day = ~2.5k rows              | ~2,500 rows / trading day                   |
| `gme_ods_price_history`                           | 5y × 252 = ~1,260 rows                        | 1 row / trading day                         |
| `dim_date`                                        | ~2,920 rows (8 years)                         | (table refresh only)                        |
| `dim_holidays`                                    | ~80 rows                                      | (table refresh only)                        |
| `dim_macro_events`                                | ~600 rows                                     | (table refresh only)                        |
| `gme_dwd_options_chain`                           | ~2,500 rows                                   | ~2,500 rows / trading day                   |
| `gme_dwd_options_chain_greeks`                    | ~2,500 rows                                   | ~2,500 rows / trading day                   |
| `gme_dwd_price_eod`                               | ~1,260 rows                                   | 1 row / trading day                         |
| `gme_dws_perf_max_pain`                           | ~20 rows (one per expiry)                     | ~20 rows / trading day                      |
| `gme_dws_perf_implied_vol`                        | ~1,260 rows                                   | 1 row / trading day                         |
| `gme_dws_perf_dealer_gamma`                       | 1 row × steady-state count                    | 1 row / trading day                         |
| `gme_dws_perf_dealer_gamma_front_month`           | 1 row × steady-state count                    | 1 row / trading day                         |
| `gme_ads_market_dashboard`                        | 1 row (view, on-demand)                       | 1 row (view, on-demand at each query)       |

DuckDB / MotherDuck: total steady-state on-disk footprint is well
under 1 GB for the full eight-year coverage window.

---

## T-16: Coding

### Naming Conventions

- ODS: `gme_ods_<source>_<entity>` (e.g. `gme_ods_options_chain_snapshot`, `gme_ods_price_history`).
- DIM: `dim_<entity>` (e.g. `dim_date`).
- DWD: `gme_dwd_<entity>` (e.g. `gme_dwd_options_chain`, `gme_dwd_options_chain_greeks`, `gme_dwd_price_eod`).
- DWS: `gme_dws_<agg_type>_<entity>` (e.g. `gme_dws_perf_implied_vol`, `gme_dws_perf_max_pain`).
- ADS: `gme_ads_<use_case>` (e.g. `gme_ads_market_dashboard`).

### dbt Project Structure

```
models/
  ods/
    gme_ods_options_chain_snapshot.sql
    gme_ods_price_history.sql
  dim/
    dim_date.sql
    dim_holidays.sql
    dim_macro_events.sql
  dwd/
    gme_dwd_options_chain.sql
    gme_dwd_options_chain_greeks.sql
    gme_dwd_price_eod.sql
  dws/
    gme_dws_perf_max_pain.sql
    gme_dws_perf_implied_vol.sql
    gme_dws_perf_dealer_gamma.sql
    gme_dws_perf_dealer_gamma_front_month.sql
  ads/
    gme_ads_market_dashboard.sql
  schema.yml
seeds/
  dim_date.csv
  dim_holidays.csv
  dim_macro_events.csv
tests/
  max_pain_in_strike_set.sql
  max_pain_fixture_asymmetric_chain.sql
  dealer_net_gamma_neq_net_gex.sql
  dealer_net_gamma_scope_distinct.sql
  iv_rank_implies_label_final.sql
  iv_rank_fixture_synthetic_252d.sql
  gex_zero_cross_in_strike_set.sql
```

The Streamlit dashboard sits at
`examples/gme-options-mart/dashboard/app.py` and reads
`gme_ads_market_dashboard` either from MotherDuck (live mode) or from
a local DuckDB fixture (fallback mode); see T-17.

---

## T-17: Dashboard Specification

| Dashboard Panel                                | Chart Type | Metrics Displayed                                                       | Filter Dimensions             | Link-status display                                                                                                       |
|------------------------------------------------|------------|-------------------------------------------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| Header banner                                  | Text       | `trading_date`, `last_pull_ts_utc`, `pull_lag_hours`, STALE flag         | (none)                        | Connection banner: "Connected to MotherDuck" (live) / "local DuckDB fixture mode" (fallback). STALE banner if `is_stale`. The ADS is a **view** (T-6 / T-15); `most_recent_session_close_ts_utc`, `pull_lag_hours`, and `is_stale` re-evaluate at every dashboard `SELECT` — Monday-morning queries against an unrefreshed warehouse correctly fire STALE without depending on a fresh `dbt run`. |
| Spot tile                                      | Metric     | `spot`                                                                  | (none)                        | Badge → `https://finance.yahoo.com/quote/GME/history?period1=...` (clickable, link_status = exact).                          |
| Max pain (front expiry) tile                   | Metric     | `max_pain_strike_front` + front expiry date label                       | (none)                        | Badge → `https://max-pain.com/stocks/GME` (clickable).                                                                       |
| P/C OI tile                                    | Metric     | `pc_ratio_oi`                                                            | (none)                        | Badge → `https://barchart.com/stocks/quotes/GME/put-call-ratios` (clickable).                                                |
| IV30 tile                                      | Metric     | `iv30`                                                                   | (none)                        | Badge → `https://marketchameleon.com/Overview/GME/` (clickable, proxy).                                                       |
| HV20 tile                                      | Metric     | `hv20`                                                                   | (none)                        | Badge → `https://barchart.com/stocks/quotes/GME/price-history/historical` (clickable).                                       |
| Net GEX tile                                   | Metric     | `net_gex` (USD per 1% scaled to millions for display)                    | (none)                        | Badge: unsupported (grey, non-clickable).                                                                                    |
| Strike-axis GEX zero cross @ current spot tile | Metric     | `gex_zero_cross_strike`                                                  | (none)                        | Badge: unsupported (grey).                                                                                                   |
| Dealer net gamma (front month) tile            | Metric     | `dealer_net_gamma` (shares per 1%)                                       | (none)                        | Badge: unsupported (grey).                                                                                                   |
| IV Rank tile                                   | Metric     | `iv_rank`, `iv_rank_label`, `iv_rank_lookback_days`                       | (none)                        | Badge driven by `iv_rank_link_status_active`: 'unsupported' (grey, "provisional, lookback Nd/252") OR 'proxy' clickable → `https://marketchameleon.com/Overview/GME/IV/`. |
| Sidebar: link-status legend                    | List       | one row per metric tile                                                  | (none)                        | Each row carries the same badge as its tile (clickable for exact/proxy, grey for unsupported).                                |
| Refresh button                                 | Action     | re-queries `gme_ads_market_dashboard` bypassing Streamlit cache          | (none)                        | (no badge)                                                                                                                  |

Connection mode: dashboard probes `MOTHERDUCK_TOKEN` env var; if
present, opens `md:gme_db` and shows "Connected to MotherDuck"; else
opens local DuckDB fixture at
`examples/gme-options-mart/data/fixtures/gme.duckdb` and shows
"local DuckDB fixture mode" (T7.2 / T7.3).

---

## T-18: DQC Plan

| Check Name                                     | Layer | Table                                            | Rule                                                                                                                              | Threshold                  |
|------------------------------------------------|-------|--------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| pk_chain_snapshot                              | ODS   | `gme_ods_options_chain_snapshot`                  | `(trading_date, expiry_date, strike, option_type)` unique and not-null.                                                            | 0 violations               |
| pk_price_history                               | ODS   | `gme_ods_price_history`                           | `trading_date` unique and not-null.                                                                                                | 0 violations               |
| freshness_chain                                | ODS   | `gme_ods_options_chain_snapshot`                  | `MAX(pull_ts_utc) - most_recent_session_close <= 26h`.                                                                              | 26 hours                   |
| freshness_price                                | ODS   | `gme_ods_price_history`                           | `MAX(pull_ts_utc) - most_recent_session_close <= 26h`.                                                                              | 26 hours                   |
| volume_chain                                   | ODS   | `gme_ods_options_chain_snapshot`                  | row count within ±20% of trailing 5-day median for the trading_date.                                                                 | 20%                        |
| fk_dim_date                                    | DWD   | `gme_dwd_options_chain`                           | `date_sk` and `expiry_date_sk` resolve to `dim_date.date_sk`.                                                                       | 0 violations               |
| not_null_dwd                                   | DWD   | `gme_dwd_options_chain`                           | required columns (trading_date, expiry_date, strike, option_type) are not null.                                                     | 0 violations               |
| accepted_range_oi                              | DWD   | `gme_dwd_options_chain`                           | `open_interest >= 0`.                                                                                                                | 0 violations               |
| accepted_range_iv                              | DWD   | `gme_dwd_options_chain`                           | `implied_volatility IS NULL OR (implied_volatility > 0 AND implied_volatility < 10)`.                                                | 0 violations               |
| duplicate_detection                            | DWD   | `gme_dwd_options_chain`                           | no duplicate `(trading_date, expiry_date, strike, option_type)` after dedup.                                                         | 0 duplicates               |
| business_recon_max_pain                        | DWS   | `gme_dws_perf_max_pain`                           | `max_pain_strike` ∈ distinct strike set for `(trading_date, expiry_date)` (closes predecessor `bae4af2` cross-join cardinality bug). | 0 violations               |
| business_recon_dealer_net_gamma_neq_net_gex    | DWS   | `gme_dws_perf_dealer_gamma_front_month`           | T3.4 numerical predicate (item B): `abs(dealer_net_gamma - net_gex / (spot²·0.01)) > 0.01 * abs(dealer_net_gamma)` whenever back-month OI > 0. | per-row pass               |
| dealer_net_gamma_scope_distinct                | DWS   | `gme_dws_perf_dealer_gamma_front_month`           | T3.4 structural predicate: `gme_dws_perf_dealer_gamma.n_rows_used > gme_dws_perf_dealer_gamma_front_month.n_rows_used` whenever back-month rows exist; `scope_label` differs. | 0 violations               |
| business_recon_iv_rank_label                   | DWS   | `gme_dws_perf_implied_vol`                        | `iv_rank IS NULL OR iv_rank_label = 'final'`; `iv_rank_label = 'final' iff iv_rank_lookback_days >= 252`.                            | 0 violations               |
| business_recon_gex_zero_cross_in_strike_set    | DWS   | `gme_dws_perf_dealer_gamma_front_month`           | `gex_zero_cross_strike IS NULL OR EXISTS (front_month strike between K_below and K_above)` per the algorithm.                       | 0 violations               |
| iv_rank_link_status_active_lifecycle           | ADS   | `gme_ads_market_dashboard`                        | When `iv_rank_lookback_days < 252` then `iv_rank_link_status_active = 'unsupported'`; when `>= 252` then `'proxy'`. **Owned by Phase D `/mart-dqc`** (reviewer item E): the flip is enforced by the ADS model formula in T-14, and `/mart-dqc` validates per-run that the formula's output matches the contract; no separate mutable-state machinery is needed. | 0 violations               |
| business_recon_t1_6b_floor                     | DWS   | `gme_dws_perf_dealer_gamma`                       | T1.6b denominator floor (item D): when `abs(producer_net_gex) < 1e6` USD the relative-spread assertion is skipped and the absolute spread is asserted instead (`max(net_gex_at_r) − min(net_gex_at_r) <= 1e4`). | per-row pass               |

---

## T-19: Test Case

| Test ID | Layer | Table                                          | Test Type           | Description                                                                                                                                                | Expected Result |
|---------|-------|------------------------------------------------|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| TC-01   | ODS   | `gme_ods_options_chain_snapshot`                | unique              | `(trading_date, expiry_date, strike, option_type)` primary-key uniqueness.                                                                                  | 0 failures      |
| TC-02   | ODS   | `gme_ods_options_chain_snapshot`                | not_null            | `trading_date`, `expiry_date`, `strike`, `option_type` not null.                                                                                            | 0 failures      |
| TC-03   | ODS   | `gme_ods_price_history`                         | unique              | `trading_date` primary-key uniqueness.                                                                                                                       | 0 failures      |
| TC-04   | DWD   | `gme_dwd_options_chain`                         | relationships       | `date_sk` FK resolves to `dim_date.date_sk`.                                                                                                                | 0 failures      |
| TC-05   | DWD   | `gme_dwd_options_chain_greeks`                  | accepted_values     | `sign_dealer` ∈ {-1, 1}.                                                                                                                                    | 0 failures      |
| TC-06   | DWS   | `gme_dws_perf_max_pain`                         | singular            | `max_pain_in_strike_set.sql` — closes T3.3 / predecessor cross-join bug.                                                                                     | 0 failures      |
| TC-07   | DWS   | `gme_dws_perf_dealer_gamma_front_month`         | singular            | `dealer_net_gamma_neq_net_gex.sql` — item B's 1%-of-`abs(dealer_net_gamma)` epsilon predicate, conditional on back-month OI > 0.                              | 0 failures      |
| TC-08   | DWS   | `gme_dws_perf_dealer_gamma_front_month`         | singular            | `dealer_net_gamma_scope_distinct.sql` — `n_rows_used` and `scope_label` differ from full-chain (T3.4 structural predicate).                                  | 0 failures      |
| TC-09   | DWS   | `gme_dws_perf_implied_vol`                      | singular            | `iv_rank_implies_label_final.sql` — closes T3.5 / predecessor null-without-label bug.                                                                        | 0 failures      |
| TC-10   | DWS   | `gme_dws_perf_dealer_gamma_front_month`         | singular            | `gex_zero_cross_in_strike_set.sql` — `gex_zero_cross_strike` lies between two existing front-month strikes (closes reviewer items C + finding 3).            | 0 failures      |
| TC-11   | ADS   | `gme_ads_market_dashboard`                      | accepted_values     | `iv_rank_link_status_active` ∈ {'unsupported', 'proxy'}; `'proxy'` iff `iv_rank_lookback_days >= 252` (item E).                                              | 0 failures      |
| TC-12   | ADS   | `gme_ads_market_dashboard`                      | accepted_values     | `is_stale = NOT (pull_lag_hours >= 0 AND pull_lag_hours <= 26)` (T2 freshness contract from BRD L-7).                                                        | 0 failures      |
| TC-13   | tests | `tests/test_net_gex_recompute.py`               | python              | T1.6 same-r parity at `r=0.045`, ±1% tolerance.                                                                                                              | 0 failures      |
| TC-14   | tests | `tests/test_net_gex_rate_sensitivity.py`        | python              | T1.6b parametric at `r ∈ {0.03, 0.045, 0.06}`; relative-spread test with `max(abs(producer), 1e6 USD)` floor (item D).                                       | 0 failures      |
| TC-15   | tests | `tests/test_gex_zero_cross_strike_recompute.py` | python              | T1.7 front-month-only strike-axis recompute, ±$0.50 on the interpolated strike, tie-break = nearest spot / lower on equidistant ties (item C).                | 0 failures      |
| TC-16   | DWS   | `gme_dws_perf_max_pain`                         | singular            | `max_pain_fixture_asymmetric_chain.sql` — asymmetric synthetic chain (1,000 calls @ K_under=20, 1,000 puts @ K_under=30) asserts `max_pain_strike ∈ [20, 30]`. Would FAIL under the round-1 swapped-terms formula (closes Phase B.5 finding 1). | 0 failures      |
| TC-17   | DWS   | `gme_dws_perf_implied_vol`                      | singular            | `iv_rank_fixture_synthetic_252d.sql` — synthetic 252-day iv30 series with a known monotonic distribution; assert `iv_rank` of the last row matches the analytically known percentile within ±0.1. Would FAIL under `percent_rank() OVER (ORDER BY iv30)` (closes Phase B.5 finding 2). | 0 failures      |

---

## T-20: Job Monitoring and Alerts

| Job Name                       | Schedule                  | SLA                                                  | Alert Channel | Escalation                                  |
|--------------------------------|---------------------------|------------------------------------------------------|---------------|---------------------------------------------|
| `daily_pipeline`               | `30 21 * * 1-5` UTC       | T+2h (per `mart.yml.refresh.sla_hours`)              | GitHub Actions failure email | Retry once; if still failing, surface as PR-blocking CI failure on next push. |
| `dqc_checks`                   | post-run on each push     | T+5 min                                              | GitHub Actions output         | Block CI green status; failure means PR cannot merge.                          |
| `dashboard_smoke`              | post-run on each push     | T+2 min                                              | GitHub Actions output         | Block CI green status.                                                          |

### Open questions (carry into Phase C)

- **OQ-1** Initial cold-start pull strategy: do we hand-seed
  `gme_dws_perf_implied_vol` from an external IV history snapshot at
  t₀, or accept ~12 months of `provisional` IV rank? Phase A L-3
  documents the accept-provisional path; Phase D `/mart-dqc` will own
  the lifecycle flip per item E.
- **OQ-2** Risk-free-rate ingest (BRD L-4): the Fred 3M T-bill ingest
  pipeline is queued for Phase D follow-up. Pre-flip behavior pins
  `r = 0.045`; T1.6b parametric test (item D) covers the rate-band
  claim independently in the meantime.

---

## T-21: Notable / Known Limitations

| ID   | Limitation Description                                                                                              | Impact                                                          | Mitigation                                                                                                                                                                                                                                                                                                                                                                  |
|------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| TL-1 | Carry-forward of BRD L-1: yfinance is unofficial; upstream schema can change.                                       | Pulls can break with parse errors mid-day.                      | Ingest layer logs raw response on parse failure; CI runs a synthetic-fixture round-trip so dbt + dashboard layers are exercised without live yfinance.                                                                                                                                                                                                                       |
| TL-2 | Carry-forward of BRD L-2 + L-4: greek inputs (IV, r) are model-derived / hard-coded.                                | Greek values can shift with chosen r; vendor IV may differ.     | iv30 link_status = proxy with ±5% tolerance; T1.6b parametric test asserts L-4's rate-insensitivity claim with the near-zero floor at $1e6 (item D).                                                                                                                                                                                                                          |
| TL-3 | Carry-forward of BRD L-3 + item E: iv_rank `link_status_active` is mutable state at the data-warehouse boundary.    | The catalog is dogfooded frozen; the active link_status flips once when the rolling window first hits 252 trading days. | The flip is implemented as a deterministic SQL formula in T-14 ADS column `iv_rank_link_status_active = CASE WHEN iv_rank_lookback_days >= 252 THEN 'proxy' ELSE 'unsupported' END`. No mutable state machinery is needed. Phase D `/mart-dqc` validates per run that the formula matches the contract; the source_catalog's `link_status_active` field is read-only documentation of the cold-start phase. |
| TL-4 | Carry-forward of BRD L-7: freshness must be a single inequality. T2.1/T2.2/T2.3 in TEST PLAN evaluate the same predicate on `pull_lag_hours`. ADS materialised as a view so the inequality is re-evaluated at every dashboard query (closes Phase B.5 finding 3). | Producer/validator drift on "pull age" semantics killed round-1 dashboard behavior; a table-materialised ADS would only re-fire STALE at `dbt run`, hiding weekend / Monday-morning staleness. | `gme_ads_market_dashboard` materialised as `view`; `is_stale = NOT (pull_lag_hours >= 0 AND pull_lag_hours <= 26)` recomputed per query against query-time `current_date`/`now()`; TC-12 enforces. |
| TL-5 | New limitation: front-month `gex_zero_cross_strike` may have multiple sign changes on days with heavy put + call walls. | Reviewer item C: algorithm needs a deterministic tie-break.    | T-13 step 6 ties broken by `argmin abs(K* − spot)`; equidistant ties go to the lower strike. TC-10 + `gex_zero_cross_n_candidates` provenance column expose multi-crossing days to the dashboard.                                                                                                                                                                              |
| TL-6 | New limitation: dbt incremental on `gme_dws_perf_implied_vol` self-references prior rows for the 252-day rolling window. | Backfills must rebuild the model in trading_date order.        | dbt config uses `unique_key='trading_date'` with `incremental_strategy='delete+insert'`; backfill procedure documented in Phase D `/mart-dqc` runbook.                                                                                                                                                                                                                          |

---

## Signature

| Role          | Name                       | Date       | Signature                                                                                |
|---------------|----------------------------|------------|------------------------------------------------------------------------------------------|
| Stakeholder   | ________________            | __________ | (unsigned — Phase B.5 round-2 review pending)                                                    |
| Data Engineer | ________________            | __________ | (unsigned — Phase B.5 round-2 review pending)                                                    |
