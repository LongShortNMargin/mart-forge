# Business Requirements Document: gme-options-mart

> **Date:** 2026-06-01
> **Author:** mart-forge example author
> **Status:** Draft (round 2 — addresses reviewer findings 1-12 in comment `8bd7a35c`)

---

## B-1: Version History

| Version | Date       | Author                       | Changes                                                                                                                                                                                                                                                                                |
|---------|------------|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 0.1     | 2026-06-01 | mart-forge example author    | Initial draft from `docs/source_catalog.json`.                                                                                                                                                                                                                                          |
| 0.2     | 2026-06-01 | mart-forge example author    | Round-2 revision addressing reviewer findings 1-12: single locked GEX sign convention; dealer_net_gamma scope-distinct (front-month-only) from net_gex (full-chain); gex_zero_cross_strike renamed; iv30 interpolation pinned to total variance; iv_rank link_status phase-gated; freshness threshold aligned; minor language fixes. |

---

## B-2: Business Context

### Business Process

The mart supports daily monitoring of the listed-options market for a
single US-listed equity ticker (`GME`). The operational process being
modeled is **end-of-day options-chain analytics**: every trading day at
~21:00 UTC the universe of listed call/put contracts is snapshotted,
the underlying close price is recorded, and a fixed set of derived
risk metrics (max pain, put/call ratio, implied volatility, realized
volatility, net GEX, strike-axis GEX zero-cross, dealer net gamma) are
recomputed for that trading_date. The mart is a public canonical
example for the `mart-forge` framework — its purpose is to demonstrate
the full lifecycle (source-discovery → BRD → TDD → bootstrap → DQC →
dashboard) end-to-end against a real, free, publicly-available data
source with external comparators.

### Purpose

Enable analysts and developers evaluating `mart-forge` to:

1. Read a one-screen executive summary of the GME options surface for
   the most recent trading day.
2. See, beside each numeric tile, a **link-status badge** that points
   to the external comparator that was used to validate the figure
   within the documented tolerance (TEST PLAN §Tier 1).
3. Reproduce every figure locally from the same JSON source catalog
   without paid feeds or proprietary models.

The mart is not intended as a trading signal, a position recommender,
or a real-time risk monitor. It is a published reference
implementation.

### Stakeholders

| Role              | Name / Team                        | Interest                                                                          |
|-------------------|------------------------------------|-----------------------------------------------------------------------------------|
| Business Owner    | mart-forge maintainer org          | Wants a single canonical example that proves the framework's quality methodology. |
| Data Consumer     | external evaluators of mart-forge  | Want a dashboard whose numbers match independent third-party sources.             |
| Engineering Owner | mart-forge plugin pack authors     | Want the example to dogfood every lifecycle skill end-to-end.                     |

### Dealer Assumption (locked sign convention — closes reviewer finding 1)

**Dealer is short customer call gamma and long customer put gamma.**

Black-Scholes gamma is positive for both call and put on the same
`(K, T, σ)`. The dealer's gamma contribution from a customer position
with open interest `OI` is therefore `−γ·OI` for calls and `+γ·OI`
for puts.

The implied sign function used in every GEX / dealer-gamma formula in
this mart is:

| option_type | sign_dealer |
|-------------|-------------|
| call        | **−1**      |
| put         | **+1**      |

This single definition is sourced from
`source_catalog.json:dealer_assumption.implied_sign_function` and is
not allowed to drift between artifacts. The prior iteration's
contradictory sign annotations are removed.

### Domain Glossary

| Term                          | Definition                                                                                                                                                                                                                |
|-------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| spot                          | Regular-session close of GME common stock, in USD, for a given trading_date (sourced from Yahoo's `v8/finance/chart` endpoint OHLC for that trading_date — not the quote header's "Previous Close" field).                |
| open interest (OI)            | Number of options contracts outstanding (neither exercised nor closed) for a (strike, expiry, type).                                                                                                                       |
| max pain                      | Strike at which the dollar value of expiring in-the-money OI is minimized for the chosen expiry, with strikes deduplicated per side before summation.                                                                      |
| put/call ratio                | Σ(put OI) / Σ(call OI) across the full options chain on a trading day.                                                                                                                                                     |
| iv30                          | Open-interest-weighted at-the-money implied volatility interpolated to a constant 30-calendar-day tenor by linear interpolation in **total variance (σ²·t)**, annualized.                                                  |
| hv20                          | Annualized standard deviation of trailing 20 daily log returns of the underlying.                                                                                                                                          |
| gamma                         | Black-Scholes second derivative of option value with respect to spot; per-share rate of delta change. Equal for call and put at the same (K, T, σ).                                                                        |
| sign_dealer                   | Signed scalar implied by the dealer assumption: −1 for calls, +1 for puts. Used in every aggregate that purports to reflect dealer positioning.                                                                            |
| net_gex                       | Σ over the **full chain** (all listed expiries) of `γ · OI · 100 · spot² · 0.01 · sign_dealer`, in USD per 1% spot move.                                                                                                   |
| dealer_net_gamma              | Σ over the **front-month expiry only** of `γ · OI · 100 · sign_dealer`, in shares per 1% spot move. Distinct from `net_gex` by both scope (front-month-only vs full-chain) AND unit (shares vs USD).                       |
| gex_zero_cross_strike         | Strike on the chain at which the running cumulative sum of per-strike GEX (evaluated at current spot s₀, sorted ascending by strike) changes sign, for the front-month expiry. **Strike-axis diagnostic, NOT a spot price.** |
| iv rank                       | Percentile of the current iv30 within the trailing 252-trading-day distribution of iv30 (0–100).                                                                                                                           |

### Data Sources

| Source Name      | Source System                                | Extraction Method                                                                                                                       | Grain                                       | Freshness          | Verification Result |
|------------------|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------|--------------------|---------------------|
| yfinance options | finance.yahoo.com options (v7 endpoint)      | `GET https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix_expiry_seconds>` per expiry                                     | one row per (date, expiry, strike, type)    | EOD (~21:00 UTC)   | Verified            |
| yfinance prices  | finance.yahoo.com chart (v8 endpoint)        | `GET https://query2.finance.yahoo.com/v8/finance/chart/GME?interval=1d&range=<window>`                                                  | one row per trading_date                    | EOD                | Verified            |
| dim_date seed    | generated                                    | `pandas_market_calendars` XNYS schedule                                                                                                  | one row per calendar date                   | committed to repo  | Verified            |
| dim_holidays seed| generated                                    | `pandas_market_calendars` XNYS holidays                                                                                                  | one row per holiday date                    | committed to repo  | Verified            |
| dim_macro_events seed | manually curated                        | hand-curated CSV (FOMC, CPI, earnings) for the dim_date coverage window (2020-01-01 through 2027-12-31)                                  | one row per event date                      | committed to repo  | Verified            |

> **Verification**: Each source above has been called from a Python REPL
> against a non-market-holiday weekday and confirmed to return a
> non-empty payload with the expected columns. The yfinance pulls are
> deterministic at end-of-day; intraday calls are out of scope.

---

## B-3: Metrics Breakdown

| metric_name             | metric_definition                                                                                                                                                                                                                                                                                                                                  | expected_grain                          | source_type | link_status   | source_provider | source_asset                                                                                                                                  | priority | public_classification | candidate_verification_evidence                                                                                                                                                                                                                                                                                                                                |
|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------|-------------|---------------|-----------------|-----------------------------------------------------------------------------------------------------------------------------------------------|----------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| spot                    | Regular-session close of GME for the trading_date the mart used.                                                                                                                                                                                                                                                                                   | one row per trading_date                | native      | exact         | yfinance        | `https://query2.finance.yahoo.com/v8/finance/chart/GME?interval=1d&range=5d` → `chart.result[0].indicators.quote[0].close[i]`                  | high     | public                | Compared against the same Yahoo v8 chart endpoint OHLC bar for the trading_date in question (not the quote header's "Previous Close"); tolerance: exact to the cent. (Closes reviewer finding 9.)                                                                                                                                                              |
| max_pain                | Strike minimizing aggregate ITM dollar OI for the nearest unexpired weekly expiry, with strikes deduplicated per side before summation.                                                                                                                                                                                                            | one row per (trading_date, expiry_date) | derived     | exact         | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix>`                                                                          | high     | public                | Cross-checked against `max-pain.com/stocks/GME` and `chartexchange.com/symbol/nyse-gme/optionchain`; tolerance: ≤ $1 from either.                                                                                                                                                                                                                              |
| pc_ratio_oi             | Σ(put OI) / Σ(call OI) across the full GME options chain on the most recent trading_date.                                                                                                                                                                                                                                                          | one row per trading_date                | derived     | exact         | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix>` — all expiries                                                           | high     | public                | Cross-checked against Barchart's **"OI Ratio" column on the "All" (chain-wide) row** of `barchart.com/stocks/quotes/GME/put-call-ratios` (free tier); tolerance: ±5%. The "All" row is specified to disambiguate from 5-day/20-day volume rows (closes reviewer finding 11).                                                                                    |
| iv30                    | OI-weighted ATM implied volatility, interpolated to constant 30-calendar-day tenor by linear interpolation **in total variance (σ²·t)**, annualized.                                                                                                                                                                                                | one row per trading_date                | derived     | proxy         | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix>` — bracketing expiries                                                    | high     | public                | Cross-checked against `marketchameleon.com/Overview/GME/` IV30 (free tier); tolerance: ±5%. Marked proxy because Market Chameleon's surface fit is vendor-proprietary; the interpolation rule is pinned to "linear in σ²·t" so producer and validator implement identical math (closes reviewer finding 5).                                                     |
| hv20                    | Annualized stddev of trailing 20 daily log returns of GME close.                                                                                                                                                                                                                                                                                   | one row per trading_date                | derived     | exact         | yfinance        | `https://query2.finance.yahoo.com/v8/finance/chart/GME?interval=1d&range=2mo`                                                                  | high     | public                | Cross-checked against Barchart 20-day Historical Volatility on `barchart.com/stocks/quotes/GME/price-history/historical`; tolerance: ±10%.                                                                                                                                                                                                                       |
| net_gex                 | Σ over **full chain** (all listed expiries) of `γ · OI · 100 · spot² · 0.01 · sign_dealer(type)`, in USD per 1% spot move. Sign convention is locked: `sign_dealer(call) = −1`, `sign_dealer(put) = +1`.                                                                                                                                            | one row per trading_date                | derived     | unsupported   | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix>` — all expiries                                                           | high     | public                | No free public comparator publishes a numerically-comparable chain-wide dealer Net GEX (see §B-4 exhaustion log). Validated by TEST PLAN T1.6 (same-r parity) AND T1.6b (parametric sensitivity at r ∈ {0.03, 0.045, 0.06}, ≤ 1% spread — closes reviewer finding 4).                                                                                            |
| gex_zero_cross_strike   | Strike on the chain at which the running cumulative sum of per-strike GEX (evaluated at current spot s₀, sorted ascending by strike) changes sign, for the front-month expiry. **Strike-axis diagnostic — NOT a spot-price root-find.** Dashboard tile label: "Strike-axis GEX zero cross @ current spot". (Renamed from `gamma_flip` per reviewer finding 3.) | one row per trading_date                | derived     | unsupported   | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix_front_expiry>`                                                             | medium   | public                | No free public comparator (see §B-4 exhaustion log). Validated by TEST PLAN T1.7 (front-month expiry only, ±$0.50 on the interpolated strike — closes reviewer findings 3 + 8).                                                                                                                                                                                  |
| iv_rank                 | Percentile of current iv30 within trailing 252-trading-day rolling distribution of iv30 (0–100). Null with `iv_rank_label='provisional'` until the rolling window has 252 non-null iv30 observations.                                                                                                                                              | one row per trading_date                | derived     | unsupported   | internal        | `gme_dws_perf_implied_vol.iv30` (rolling 252-trading-day window)                                                                               | medium   | public                | **Phase-gated link_status (closes reviewer finding 6):** while `iv_rank_lookback_days < 252` the metric is `unsupported` (cold-start, evidence in §B-4 L-3). When `iv_rank_lookback_days >= 252` link_status flips to `proxy` against `marketchameleon.com/Overview/GME/IV/` within ±5% and the dashboard renders a clickable comparator badge.                |
| dealer_net_gamma        | Σ over the **front-month expiry only** of `γ · OI · 100 · sign_dealer(type)`, in shares per 1% spot move. Distinct from `net_gex` by **two axes**: scope (front-month-only vs full-chain) AND unit (shares vs USD). Closes reviewer finding 2.                                                                                                     | one row per trading_date                | derived     | unsupported   | yfinance        | `https://query2.finance.yahoo.com/v7/finance/options/GME?date=<unix_front_expiry>`                                                             | medium   | public                | No free public comparator (see §B-4 exhaustion log). Validated by TEST PLAN T3.4 which asserts the structural scope distinction (front-month-only vs full-chain) and rejects the predecessor's identity `dealer_net_gamma == net_gex / (spot²·0.01)`.                                                                                                            |

### source_type Legend

- **native**: Metric is directly available from a single source field.
- **derived**: Metric is computed from two or more source fields.
- **hybrid**: Metric combines native extraction with a derived calculation.

### link_status Legend

- **exact**: Metric value matches a free public external source within tolerance.
- **proxy**: A related public metric is used for directional validation when no exact match exists or vendor uses a slightly different surface fit.
- **unsupported**: No free public comparator publishes a numerically-comparable figure; validated only by internal recompute and DQC.
- **unverified**: Verification has not yet been attempted (must not appear in a signed BRD).

For `iv_rank`, the link_status is **phase-gated**: `unsupported` until
`iv_rank_lookback_days >= 252`, `proxy` thereafter. The dashboard badge
follows the same rule (closes reviewer finding 6).

---

## B-4: Notable / Known Limitations

### Declared Constraints

| ID   | Constraint Description                                                                                              | Impact                                                          | Mitigation                                                                                                                                                  |
|------|---------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L-1  | yfinance is an unofficial scraper of Yahoo Finance; the upstream HTML/JSON can change without notice.               | Pulls can break mid-day with a parse error from upstream layout changes. | Ingest layer logs the raw response on parse failure; CI runs a synthetic-fixture round-trip so the dbt + dashboard layers are exercised without live yfinance. |
| L-2  | Yahoo Finance's options-chain greeks (implied volatility, gamma) are model-derived by Yahoo with an undocumented surface fit. | iv30 numbers will be directionally accurate but can disagree with vendor IV30 figures by single-digit percent. | iv30 is published with `link_status = proxy`, tolerance ±5%, and interpolation pinned to "linear in σ²·t" (closes reviewer finding 5).                                                                       |
| L-3  | iv_rank requires a 252-trading-day rolling history of iv30; on cold start that history does not exist.              | iv_rank is null for the first 252 trading days.                 | Dashboard renders the iv_rank tile with a "provisional" label and an explicit `iv_rank_lookback_days` field; link_status is phase-gated unsupported→proxy at the 252-day boundary; TEST PLAN T3.5 enforces this contract. |
| L-4  | Risk-free rate is hard-coded at 0.045 (4.5%) for Black-Scholes greek recomputation.                                  | Greek values can shift with the chosen rate; T1.6 alone (same-r parity) cannot catch a silent rate change in the producer. | T1.6b parametric sensitivity test recomputes net_gex at r ∈ {0.03, 0.045, 0.06} and asserts `(max - min) / |producer_value| <= 1%`. Fred 3M T-bill ingest queued as Phase D follow-up (closes reviewer finding 4). |
| L-5  | Pull cadence is end-of-day only; intraday GEX shifts are not captured.                                              | Mart cannot answer intraday questions.                          | Out of scope for this example; documented explicitly in §B-2 Purpose.                                                                                       |
| L-6  | Spot comparator must be aligned to the **same trading_date** the mart used (Yahoo's "Previous Close" header drifts by one trading day during market hours). | Tier-1 T1.1 would fail every intraday execution if compared to "Previous Close". | T1.1 compares against the Yahoo v8 chart endpoint OHLC bar for the trading_date in question, not the quote header (closes reviewer finding 9).                                                                |
| L-7  | Freshness threshold must be a single number; T2.1/T2.3 must not disagree.                                            | Prior iteration allowed a pull that satisfied T2.1 to also trigger T2.3 STALE banner (96h vs 72h gap). | T2.1 and T2.3 both use `pull_age <= 26h since most_recent_session_close` (closes reviewer finding 7).                                                                                                            |

### Unsupported Metrics

> Per the source-discovery resource-exhaustion protocol (SPEC §6.3),
> every entry below is reported with explicit evidence that reasonable
> public free providers were enumerated and rejected before the metric
> was declared unsupported.

| metric_name              | Reason Unsupported                                                                                                                                              | Resource-Exhaustion Evidence                                                                                                                                                                                                                                                                                                                                                                                  |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| net_gex                  | No free public source publishes a numerically-comparable chain-wide dealer GEX figure in a scrapable form.                                                       | Enumerated and rejected: SpotGamma (paid subscription, fails license check); Tier1Alpha (paid subscription); MenthorQ (paid subscription); Cboe DataShop (paid feeds); Polygon.io free tier (no greeks); Yahoo Finance public site (does not publish aggregate dealer GEX). No free public comparator survives the 5-point verification. Mitigated via TEST PLAN T1.6 (parity) + T1.6b (parametric sensitivity). |
| gex_zero_cross_strike    | Same as net_gex — gex_zero_cross_strike is downstream of the same dealer gamma calculation.                                                                      | Same exhaustion log as net_gex. Mitigated via TEST PLAN T1.7 (front-month expiry only, ±$0.50 on interpolated strike).                                                                                                                                                                                                                                                                                          |
| dealer_net_gamma         | No free public source publishes the shares-per-1% dealer gamma for a single equity ticker front-month.                                                          | Same exhaustion log as net_gex. Mitigated via TEST PLAN T3.4 structural scope assertion (front-month-only computation, NOT a unit-rescale of net_gex — closes reviewer finding 2).                                                                                                                                                                                                                              |
| iv_rank (cold-start only) | Until 252 trading days of iv30 history have accumulated, no internal percentile can be computed and no external comparator can be meaningfully cross-checked.   | The series is forward-accumulated from day 0 because Yahoo's chart endpoint does not snapshot historical implied-vol surfaces. Once the rolling window fills, link_status flips to `proxy` against `marketchameleon.com/Overview/GME/IV/` (closes reviewer finding 6).                                                                                                                                            |

---

## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | ________________ | __________ | __________ |
| Data Engineer | ________________ | __________ | __________ |
