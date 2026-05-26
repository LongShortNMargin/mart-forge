# Technical Design Document: GME Options Mart

> **Date:** 2026-05-27
> **Author:** mart-forge (Phase G Conformance)
> **Prefix:** gme
> **Status:** Draft

---

## T-1: Changelog

| Version | Date       | Author                          | Section(s) Changed | Summary of Changes |
|---------|------------|---------------------------------|---------------------|--------------------|
| 0.1     | 2026-05-27 | mart-forge (Phase G Conformance)| All                 | Initial draft      |

---

## T-2: Business Background

This mart supports daily options flow analytics for GameStop Corp. (GME). The business process tracks daily snapshots of the GME options chain from Yahoo Finance and derives key sentiment, positioning, and volatility metrics — including IV30, HV20, Max Pain, P/C Ratio, Net GEX, and IV Rank — to support quantitative research and risk assessment.

Refer to `business-requirements.md` (B-2) for full stakeholder context and domain glossary.

---

## T-3: Metrics Breakdown

| Metric Name    | Business Definition | source_type | link_status | Calculation Logic | Target Table |
|----------------|---------------------|-------------|-------------|-------------------|--------------|
| Spot Price     | Current/last closing price of GME on NYSE | native | exact | pass-through from Yahoo Finance close field | gme_ods_yahoo_spot |
| OI by Strike   | Open interest per strike per expiration for calls and puts | native | exact | pass-through from Yahoo Finance openInterest field | gme_ods_yahoo_options |
| IV per Strike  | Implied volatility per option contract | native | exact | pass-through from Yahoo Finance impliedVolatility field | gme_ods_yahoo_options |
| IV30           | 30-day interpolated ATM implied volatility | derived | proxy | Interpolate ATM IV from two expirations bracketing 30 DTE | gme_ads_daily_summary |
| HV20           | 20-day annualized realized volatility | derived | proxy | STDDEV(LN(close/prev_close)) * SQRT(252) over 20 trading days | gme_ads_daily_summary |
| Max Pain       | Strike minimizing total option intrinsic value | derived | unsupported | Cross-join strikes × OI, minimize total intrinsic loss | gme_ads_daily_summary |
| P/C Ratio      | Put-to-call open interest ratio | derived | exact | SUM(put_oi) / NULLIF(SUM(call_oi), 0) | gme_ads_daily_summary |
| Net GEX        | Net gamma exposure across all strikes | derived | unsupported | SUM(call_gex) - SUM(put_gex) where gex = bs_gamma * oi * 100 * spot | gme_ads_daily_summary |
| IV Rank        | Percentile rank of IV30 in 252-day range | derived | proxy | (iv30 - MIN(iv30) over 252d) / NULLIF(MAX(iv30) - MIN(iv30) over 252d, 0) | gme_ads_daily_summary |

---

## T-4: Design Consideration (4-Step Kimball)

### Step 1: Select the Business Process

The operational process being modeled is the **daily GME options chain snapshot and derived analytics pipeline**. Each business day, the pipeline ingests the spot price and full options chain for GME, computes derived metrics, and publishes a daily summary for dashboard consumption.

### Step 2: Declare the Grain

- **ODS (spot):** One row per symbol per trading day.
- **ODS (options):** One row per contract (strike × expiration × option_type) per trading day.
- **DWD (options detail):** One row per contract per trading day, enriched with computed Greeks.
- **DWS (daily aggregate):** One row per expiration per trading day (P/C ratio, max pain, GEX per expiration).
- **ADS (daily summary):** One row per trading day (aggregate IV30, HV20, total GEX, IV Rank).

### Step 3: Identify the Dimensions

- **dim_date:** Calendar dimension for time-series slicing (trade date, day of week, is_trading_day, month, quarter).
- **dim_expiration:** Options expiration dates with DTE calculations and expiration cycle classification (weekly, monthly, quarterly).

### Step 4: Identify the Facts

Measurable numeric facts at the declared grains:
- Spot: open, high, low, close, volume.
- Options: bid, ask, last_price, open_interest, implied_volatility, volume, computed gamma, computed GEX.
- Aggregates: iv30, hv20, max_pain_strike, pc_ratio, net_gex, iv_rank.

---

## T-5: Bus Matrix

| Dimension / Fact Table         | dim_date | dim_expiration | gme_dwd_options_daily | gme_dws_expiry_daily | gme_ads_daily_summary |
|-------------------------------|----------|----------------|-----------------------|----------------------|-----------------------|
| Daily Options Analytics       | X        | X              | X                     | X                    | X                     |

---

## T-6: Table Summary

| Layer | Table Name               | Materialization | Grain                                     | Description |
|-------|--------------------------|-----------------|-------------------------------------------|-------------|
| ODS   | gme_ods_yahoo_spot       | incremental     | One row per symbol per trading day         | Raw daily spot price snapshot from Yahoo Finance |
| ODS   | gme_ods_yahoo_options    | incremental     | One row per contract per trading day       | Raw options chain snapshot from Yahoo Finance |
| DIM   | dim_date                 | table (seed)    | One row per calendar date                  | Calendar dimension with trading day flag |
| DIM   | dim_expiration           | table           | One row per expiration date                | Options expiration dates with DTE and cycle type |
| DWD   | gme_dwd_options_daily    | table           | One row per contract per trading day       | Cleaned options with computed Greeks (gamma, GEX) |
| DWS   | gme_dws_expiry_daily     | table           | One row per expiration per trading day     | Per-expiration aggregates: max pain, P/C ratio, GEX |
| DWS   | gme_dws_perf_volatility  | table           | One row per symbol per trading day         | Volatility metrics: IV30, HV20 |
| ADS   | gme_ads_daily_summary    | table           | One row per trading day                    | Final presentation table: all derived metrics |

---

## T-7: Data Architecture Diagram

```
Yahoo Finance API
    |
    v
[ ODS Layer ]
  gme_ods_yahoo_spot       -- raw daily OHLCV
  gme_ods_yahoo_options    -- raw options chain snapshot
    |
    v
[ DIM Layer ]
  dim_date                 -- calendar seed
  dim_expiration           -- expiration dates with DTE
    |
    v
[ DWD Layer ]
  gme_dwd_options_daily    -- cleaned options + computed Greeks (gamma, GEX per strike)
    |
    v
[ DWS Layer ]
  gme_dws_expiry_daily     -- per-expiration: max pain, P/C ratio, GEX
  gme_dws_perf_volatility  -- per-day: IV30, HV20
    |
    v
[ ADS Layer ]
  gme_ads_daily_summary    -- daily: spot, IV30, HV20, max pain, P/C, net GEX, IV Rank
    |
    v
[ Dashboard / BI ]
```

---

## T-8: Table Schema Detail

> All schema sections below use the 6-column format: column_name | data_type | definition | example_value | calculation | data_source.

---

## T-9: ODS Table Columns

### dbt Project Variables

```yaml
vars:
  risk_free_rate: 0.043  # US 10-year Treasury yield [THEORETICAL]
```

The `risk_free_rate` variable is used in the Black-Scholes gamma computation (DWD layer, `gme_dwd_options_daily.d1` and `gme_dwd_options_daily.bs_gamma`). Source tag: `[THEORETICAL]` — this is a static approximation seeded from the US 10-year Treasury yield, not a live data feed. Refresh monthly or on significant rate changes. See BRD constraint L-5.

### ODS Contract Table — gme_ods_yahoo_spot

| Property              | Value                                                    |
|-----------------------|----------------------------------------------------------|
| source                | Yahoo Finance v8/finance/chart/GME                       |
| grain                 | One row per symbol per trading day                       |
| logical_partition     | trade_date                                               |
| incremental_strategy  | delete+insert                                            |
| unique_key            | (symbol, trade_date)                                     |
| backfill              | Full reload of 3-month history on initial run            |
| restatement           | Delete+insert for the affected trade_date partition      |
| provenance_columns    | provider, pull_ts_utc, run_id                            |

### gme_ods_yahoo_spot Columns

| column_name   | data_type   | definition                                      | example_value       | calculation | data_source             |
|---------------|-------------|-------------------------------------------------|---------------------|-------------|-------------------------|
| symbol        | VARCHAR     | Ticker symbol                                   | 'GME'               | --          | Yahoo Finance           |
| trade_date    | DATE        | Trading day                                     | 2026-05-27          | --          | Yahoo Finance           |
| open          | DOUBLE      | Opening price                                   | 22.00               | --          | Yahoo Finance chart.open |
| high          | DOUBLE      | Intraday high price                             | 22.50               | --          | Yahoo Finance chart.high |
| low           | DOUBLE      | Intraday low price                              | 21.80               | --          | Yahoo Finance chart.low  |
| close         | DOUBLE      | Closing price                                   | 22.15               | --          | Yahoo Finance chart.close|
| volume        | BIGINT      | Daily trading volume                            | 4054896             | --          | Yahoo Finance chart.volume|
| provider      | VARCHAR     | Name of the data provider                       | 'yahoo_finance'     | --          | system                  |
| pull_ts_utc   | TIMESTAMP   | UTC timestamp of data extraction                | 2026-05-27 20:30:00 | --          | system                  |
| run_id        | VARCHAR     | Unique identifier for the ETL run               | 'run_20260527_2030' | --          | system                  |

### ODS Contract Table — gme_ods_yahoo_options

| Property              | Value                                                    |
|-----------------------|----------------------------------------------------------|
| source                | Yahoo Finance v7/finance/options/GME (via yfinance SDK)  |
| grain                 | One row per contract per trading day                     |
| logical_partition     | trade_date                                               |
| incremental_strategy  | delete+insert                                            |
| unique_key            | (contract_symbol, trade_date)                            |
| backfill              | Snapshot of current chain on initial run (no historical options data available) |
| restatement           | Delete+insert for the affected trade_date partition      |
| provenance_columns    | provider, pull_ts_utc, run_id                            |

### gme_ods_yahoo_options Columns

| column_name        | data_type   | definition                                         | example_value              | calculation | data_source                      |
|--------------------|-------------|----------------------------------------------------|----------------------------|-------------|----------------------------------|
| contract_symbol    | VARCHAR     | Unique contract identifier                         | 'GME260529C00022000'       | --          | Yahoo Finance contractSymbol     |
| trade_date         | DATE        | Trading day of this snapshot                       | 2026-05-27                 | --          | system                           |
| symbol             | VARCHAR     | Underlying ticker                                  | 'GME'                      | --          | derived from contract_symbol     |
| expiration_date    | DATE        | Contract expiration date                           | 2026-05-29                 | --          | Yahoo Finance expirationDate     |
| strike             | DOUBLE      | Strike price                                       | 22.00                      | --          | Yahoo Finance strike             |
| option_type        | VARCHAR     | 'call' or 'put'                                   | 'call'                     | --          | derived from chain position      |
| last_price         | DOUBLE      | Last traded price                                  | 1.25                       | --          | Yahoo Finance lastPrice          |
| bid                | DOUBLE      | Best bid price                                     | 1.20                       | --          | Yahoo Finance bid                |
| ask                | DOUBLE      | Best ask price                                     | 1.30                       | --          | Yahoo Finance ask                |
| volume             | BIGINT      | Daily contract volume                              | 150                        | --          | Yahoo Finance volume             |
| open_interest      | BIGINT      | Total open interest                                | 5000                       | --          | Yahoo Finance openInterest       |
| implied_volatility | DOUBLE      | Annualized implied volatility (decimal)            | 0.85                       | --          | Yahoo Finance impliedVolatility  |
| in_the_money       | BOOLEAN     | Whether the contract is ITM                        | true                       | --          | Yahoo Finance inTheMoney         |
| provider           | VARCHAR     | Name of the data provider                          | 'yahoo_finance'            | --          | system                           |
| pull_ts_utc        | TIMESTAMP   | UTC timestamp of data extraction                   | 2026-05-27 20:30:00        | --          | system                           |
| run_id             | VARCHAR     | Unique identifier for the ETL run                  | 'run_20260527_2030'        | --          | system                           |

---

## T-10: DIM Table Columns

### dim_date Columns

| column_name      | data_type | definition                               | example_value  | calculation          | data_source |
|------------------|-----------|------------------------------------------|----------------|----------------------|-------------|
| date_key         | DATE      | Calendar date (PK)                       | 2026-05-27     | --                   | seed        |
| year             | INTEGER   | Calendar year                            | 2026           | EXTRACT(YEAR)        | generated   |
| month            | INTEGER   | Calendar month                           | 5              | EXTRACT(MONTH)       | generated   |
| day_of_week      | INTEGER   | Day of week (1=Monday)                   | 3              | EXTRACT(ISODOW)      | generated   |
| day_name         | VARCHAR   | Day name                                 | 'Wednesday'    | CASE on day_of_week  | generated   |
| is_trading_day   | BOOLEAN   | Whether US equity markets are open       | true           | seed flag            | seed        |
| quarter          | INTEGER   | Calendar quarter                         | 2              | EXTRACT(QUARTER)     | generated   |

### dim_expiration Columns

| column_name       | data_type | definition                                        | example_value  | calculation                     | data_source                |
|-------------------|-----------|---------------------------------------------------|----------------|---------------------------------|----------------------------|
| expiration_sk     | INTEGER   | Surrogate key                                     | 1              | ROW_NUMBER()                    | generated                  |
| expiration_date   | DATE      | Options expiration date                            | 2026-05-29     | --                              | gme_ods_yahoo_options      |
| cycle_type        | VARCHAR   | Expiration cycle: weekly, monthly, quarterly       | 'weekly'       | CASE on day-of-month rules      | derived                    |

---

## T-11: DWD Table Columns

### gme_dwd_options_daily Columns

| column_name        | data_type | definition                                         | example_value       | calculation                                                | data_source                |
|--------------------|-----------|----------------------------------------------------|---------------------|------------------------------------------------------------|----------------------------|
| contract_symbol    | VARCHAR   | Unique contract identifier (PK part)               | 'GME260529C00022000'| pass-through from gme_ods_yahoo_options.contract_symbol    | gme_ods_yahoo_options      |
| trade_date         | DATE      | Trading day (PK part)                              | 2026-05-27          | pass-through from gme_ods_yahoo_options.trade_date         | gme_ods_yahoo_options      |
| symbol             | VARCHAR   | Underlying ticker                                  | 'GME'               | pass-through                                                | gme_ods_yahoo_options      |
| expiration_date    | DATE      | Contract expiration date                           | 2026-05-29          | pass-through                                                | gme_ods_yahoo_options      |
| strike             | DOUBLE    | Strike price                                       | 22.00               | pass-through                                                | gme_ods_yahoo_options      |
| option_type        | VARCHAR   | 'call' or 'put'                                   | 'call'              | pass-through                                                | gme_ods_yahoo_options      |
| spot_close         | DOUBLE    | Spot closing price on trade_date                   | 22.15               | JOIN gme_ods_yahoo_spot ON (symbol, trade_date)            | gme_ods_yahoo_spot         |
| bid                | DOUBLE    | Best bid price                                     | 1.20                | pass-through                                                | gme_ods_yahoo_options      |
| ask                | DOUBLE    | Best ask price                                     | 1.30                | pass-through                                                | gme_ods_yahoo_options      |
| mid_price          | DOUBLE    | Midpoint of bid and ask                            | 1.25                | `(bid + ask) / 2.0`                                        | derived                    |
| open_interest      | BIGINT    | Total open interest                                | 5000                | pass-through                                                | gme_ods_yahoo_options      |
| implied_volatility | DOUBLE    | Annualized IV (decimal)                            | 0.85                | pass-through                                                | gme_ods_yahoo_options      |
| dte                | INTEGER   | Days to expiration                                 | 2                   | `expiration_date - trade_date`                              | derived                    |
| dte_annual_frac    | DOUBLE    | DTE as fraction of year                            | 0.00794             | `CAST(dte AS DOUBLE) / 365.0`                              | derived                    |
| d1                 | DOUBLE    | Black-Scholes d1 parameter                         | 0.312               | `(LN(spot_close / strike) + (risk_free_rate + 0.5 * implied_volatility * implied_volatility) * dte_annual_frac) / (implied_volatility * SQRT(dte_annual_frac))` | derived |
| bs_gamma           | DOUBLE    | Black-Scholes gamma                                | 0.15                | `EXP(-0.5 * d1 * d1) / (SQRT(2 * PI()) * spot_close * implied_volatility * SQRT(dte_annual_frac))` | derived |
| gex_per_strike     | DOUBLE    | Gamma exposure for this contract                   | 166125.0            | `bs_gamma * open_interest * 100 * spot_close`              | derived                    |
| is_atm             | BOOLEAN   | Whether this strike is nearest to spot             | true                | `ABS(strike - spot_close) = MIN(ABS(strike - spot_close)) OVER (PARTITION BY trade_date, expiration_date, option_type)` | derived |

---

## T-12: Count DWS Table Columns

### gme_dws_expiry_daily Columns

| column_name          | data_type | definition                                          | example_value  | calculation                                                                      | data_source             |
|----------------------|-----------|-----------------------------------------------------|----------------|----------------------------------------------------------------------------------|-------------------------|
| trade_date           | DATE      | Trading day (PK part)                               | 2026-05-27     | pass-through                                                                      | gme_dwd_options_daily   |
| expiration_date      | DATE      | Options expiration date (PK part)                   | 2026-05-29     | pass-through                                                                      | gme_dwd_options_daily   |
| dte                  | INTEGER   | Days to expiration                                  | 2              | pass-through                                                                      | gme_dwd_options_daily   |
| total_call_oi        | BIGINT    | Total call open interest                            | 25000          | `SUM(open_interest) WHERE option_type = 'call'`                                  | gme_dwd_options_daily   |
| total_put_oi         | BIGINT    | Total put open interest                             | 30000          | `SUM(open_interest) WHERE option_type = 'put'`                                   | gme_dwd_options_daily   |
| pc_ratio             | DOUBLE    | Put/call OI ratio for this expiration               | 1.20           | `SUM(CASE WHEN option_type='put' THEN open_interest ELSE 0 END) / NULLIF(SUM(CASE WHEN option_type='call' THEN open_interest ELSE 0 END), 0)` | derived |
| call_gex_total       | DOUBLE    | Total call gamma exposure                           | 500000.0       | `SUM(gex_per_strike) WHERE option_type = 'call'`                                 | gme_dwd_options_daily   |
| put_gex_total        | DOUBLE    | Total put gamma exposure                            | 350000.0       | `SUM(gex_per_strike) WHERE option_type = 'put'`                                  | gme_dwd_options_daily   |
| net_gex_expiry       | DOUBLE    | Net GEX for this expiration                         | 150000.0       | `call_gex_total - put_gex_total`                                                  | derived                 |
| max_pain_strike      | DOUBLE    | Max pain strike for this expiration                 | 22.00          | See executable SQL below | derived |

#### Max Pain Executable SQL

```sql
-- Max pain: for each candidate strike, sum total pain (intrinsic value loss
-- to option holders) across all OI. The strike with minimum total pain is max pain.
WITH strike_pain AS (
    SELECT
        candidate.strike AS pain_strike,
        oc.trade_date,
        oc.expiration_date,
        SUM(
            CASE
                WHEN oc.option_type = 'call' AND oc.strike < candidate.strike
                    THEN (candidate.strike - oc.strike) * oc.open_interest
                WHEN oc.option_type = 'put' AND oc.strike > candidate.strike
                    THEN (oc.strike - candidate.strike) * oc.open_interest
                ELSE 0
            END
        ) AS total_pain
    FROM gme_dwd_options_daily oc
    CROSS JOIN (
        SELECT DISTINCT strike
        FROM gme_dwd_options_daily
        WHERE trade_date = (SELECT MAX(pull_date) FROM gme_dwd_options_daily)
    ) candidate
    WHERE oc.trade_date = (SELECT MAX(pull_date) FROM gme_dwd_options_daily)
    GROUP BY candidate.strike, oc.trade_date, oc.expiration_date
),
ranked AS (
    SELECT
        pain_strike,
        trade_date,
        expiration_date,
        total_pain,
        ROW_NUMBER() OVER (
            PARTITION BY trade_date, expiration_date
            ORDER BY total_pain ASC
        ) AS rn
    FROM strike_pain
)
SELECT
    trade_date,
    expiration_date,
    pain_strike AS max_pain_strike,
    total_pain
FROM ranked
WHERE rn = 1
```
| atm_call_iv          | DOUBLE    | ATM call implied volatility                         | 0.85           | `implied_volatility WHERE is_atm = true AND option_type = 'call'`                | gme_dwd_options_daily   |
| atm_put_iv           | DOUBLE    | ATM put implied volatility                          | 0.90           | `implied_volatility WHERE is_atm = true AND option_type = 'put'`                 | gme_dwd_options_daily   |
| strike_count         | INTEGER   | Number of distinct strikes listed                   | 38             | `COUNT(DISTINCT strike)`                                                          | gme_dwd_options_daily   |

---

## T-13: Performance DWS Table Columns

### gme_dws_perf_volatility Columns

| column_name       | data_type | definition                                           | example_value  | calculation                                                                      | data_source             |
|-------------------|-----------|------------------------------------------------------|----------------|----------------------------------------------------------------------------------|-------------------------|
| trade_date        | DATE      | Trading day (PK)                                     | 2026-05-27     | pass-through                                                                      | gme_dws_expiry_daily + gme_ods_yahoo_spot |
| spot_close        | DOUBLE    | GME closing price                                    | 22.15          | pass-through from gme_ods_yahoo_spot.close                                        | gme_ods_yahoo_spot      |
| iv30              | DOUBLE    | 30-day interpolated ATM implied volatility           | 0.82           | Linear interpolation of ATM IV between the two expirations bracketing 30 DTE: `iv_near + (iv_far - iv_near) * (30 - dte_near) / (dte_far - dte_near)` | gme_dws_expiry_daily |
| hv20              | DOUBLE    | 20-day annualized historical volatility              | 0.65           | `STDDEV(LN(close / LAG(close, 1) OVER (ORDER BY trade_date))) OVER (ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) * SQRT(252)` | gme_ods_yahoo_spot |
| iv_hv_spread      | DOUBLE    | Spread between IV30 and HV20                         | 0.17           | `iv30 - hv20`                                                                     | derived                 |

---

## T-14: ADS / Presentation Table Columns

### gme_ads_daily_summary Columns

| column_name         | data_type | definition                                         | example_value  | calculation                                                          | data_source                       |
|---------------------|-----------|----------------------------------------------------|----------------|----------------------------------------------------------------------|-----------------------------------|
| trade_date          | DATE      | Trading day (PK)                                   | 2026-05-27     | pass-through                                                          | gme_dws_perf_volatility           |
| spot_close          | DOUBLE    | GME closing price                                  | 22.15          | pass-through                                                          | gme_dws_perf_volatility           |
| spot_change_pct     | DOUBLE    | Daily percentage change                            | 0.0084         | `(spot_close - LAG(spot_close) OVER (ORDER BY trade_date)) / LAG(spot_close) OVER (ORDER BY trade_date)` | derived |
| iv30                | DOUBLE    | 30-day implied volatility                          | 0.82           | pass-through                                                          | gme_dws_perf_volatility           |
| hv20                | DOUBLE    | 20-day historical volatility                       | 0.65           | pass-through                                                          | gme_dws_perf_volatility           |
| iv_hv_spread        | DOUBLE    | IV30 minus HV20                                    | 0.17           | pass-through                                                          | gme_dws_perf_volatility           |
| iv_rank             | DOUBLE    | IV Rank (0.0 to 1.0)                               | 0.45           | `(iv30 - MIN(iv30) OVER (ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW)) / NULLIF(MAX(iv30) OVER (ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) - MIN(iv30) OVER (ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW), 0)` | derived |
| iv_rank_lookback    | INTEGER   | Number of days in IV Rank lookback window           | 252            | `COUNT(iv30) OVER (ORDER BY trade_date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW)` | derived |
| max_pain_nearest    | DOUBLE    | Max pain strike for nearest expiration              | 22.00          | pass-through from gme_dws_expiry_daily WHERE dte = MIN(dte)          | gme_dws_expiry_daily              |
| pc_ratio_total      | DOUBLE    | Aggregate P/C ratio across all expirations          | 1.15           | `SUM(total_put_oi) / NULLIF(SUM(total_call_oi), 0)` from gme_dws_expiry_daily | gme_dws_expiry_daily |
| net_gex             | DOUBLE    | Total net GEX across all expirations                | 450000.0       | `SUM(net_gex_expiry)` from gme_dws_expiry_daily                      | gme_dws_expiry_daily              |
| total_oi            | BIGINT    | Total open interest (calls + puts, all expirations) | 150000         | `SUM(total_call_oi + total_put_oi)` from gme_dws_expiry_daily        | gme_dws_expiry_daily              |
| expirations_count   | INTEGER   | Number of active expirations                        | 17             | `COUNT(DISTINCT expiration_date)` from gme_dws_expiry_daily           | gme_dws_expiry_daily              |

---

## T-15: Physical Design

### Materialization Strategy

| Table                        | Materialization | Partition Key | Cluster Key                    |
|------------------------------|-----------------|---------------|--------------------------------|
| gme_ods_yahoo_spot           | incremental     | trade_date    | --                             |
| gme_ods_yahoo_options        | incremental     | trade_date    | expiration_date, option_type   |
| dim_date                     | table (seed)    | --            | --                             |
| dim_expiration               | table           | --            | --                             |
| gme_dwd_options_daily        | table           | --            | trade_date, expiration_date    |
| gme_dws_expiry_daily         | table           | --            | trade_date                     |
| gme_dws_perf_volatility      | table           | --            | trade_date                     |
| gme_ads_daily_summary        | table           | --            | trade_date                     |

### Storage Estimates

| Table                        | Initial Load Rows | Daily Increment | Estimated Size |
|------------------------------|-------------------|-----------------|----------------|
| gme_ods_yahoo_spot           | ~63 (3 months)    | 1               | < 1 KB         |
| gme_ods_yahoo_options        | ~1,200 (est.)     | ~1,200          | ~100 KB/day    |
| gme_dwd_options_daily        | ~1,200            | ~1,200          | ~150 KB/day    |
| gme_dws_expiry_daily         | ~17               | ~17             | < 5 KB/day     |
| gme_dws_perf_volatility      | ~63               | 1               | < 1 KB         |
| gme_ads_daily_summary        | ~63               | 1               | < 1 KB         |

---

## T-16: Coding

### Naming Conventions

- ODS: `gme_ods_<source>_<entity>` (e.g., `gme_ods_yahoo_spot`)
- DIM: `dim_<entity>` (e.g., `dim_date`)
- DWD: `gme_dwd_<entity>_<grain>` (e.g., `gme_dwd_options_daily`)
- DWS: `gme_dws_<agg_type>_<entity>` (e.g., `gme_dws_expiry_daily`, `gme_dws_perf_volatility`)
- ADS: `gme_ads_<use_case>` (e.g., `gme_ads_daily_summary`)

### dbt Project Structure

```
models/
  ods/
    gme_ods_yahoo_spot.sql
    gme_ods_yahoo_options.sql
  dim/
    dim_date.sql
    dim_expiration.sql
  dwd/
    gme_dwd_options_daily.sql
  dws/
    gme_dws_expiry_daily.sql
    gme_dws_perf_volatility.sql
  ads/
    gme_ads_daily_summary.sql
  schema.yml
seeds/
  dim_date.csv
scripts/
  ingest_yahoo_spot.py
  ingest_yahoo_options.py
```

---

## T-17: Dashboard Specification

| Dashboard Panel         | Chart Type       | Metrics Displayed                         | Filter Dimensions            |
|-------------------------|------------------|-------------------------------------------|------------------------------|
| Spot Price              | Line             | spot_close, spot_change_pct               | date_range                   |
| Volatility Regime       | Dual-axis line   | iv30, hv20, iv_hv_spread                  | date_range                   |
| IV Rank Gauge           | Gauge / Bar      | iv_rank, iv_rank_lookback                 | date_range                   |
| GEX Profile             | Bar (per-strike) | gex_per_strike (calls positive, puts negative) | date, expiration_date   |
| Net GEX Time Series     | Line             | net_gex                                   | date_range                   |
| Max Pain vs Spot        | Line + marker    | spot_close, max_pain_nearest              | date_range                   |
| P/C Ratio               | Line             | pc_ratio_total                            | date_range                   |
| OI Distribution         | Stacked bar      | total_call_oi, total_put_oi by expiration | date                         |

---

## T-18: DQC Plan

| Check Name           | Layer | Table                     | Rule                                              | Threshold       |
|----------------------|-------|---------------------------|----------------------------------------------------|-----------------|
| freshness            | ODS   | gme_ods_yahoo_spot        | MAX(pull_ts_utc) < N hours ago                     | 24 hours        |
| freshness            | ODS   | gme_ods_yahoo_options     | MAX(pull_ts_utc) < N hours ago                     | 24 hours        |
| completeness         | DWD   | gme_dwd_options_daily     | Non-null ratio for strike, open_interest, implied_volatility >= threshold | 95%  |
| null_rate            | DWD   | gme_dwd_options_daily     | Null ratio for bs_gamma, gex_per_strike <= threshold | 5%            |
| volume_deviation     | ODS   | gme_ods_yahoo_options     | Row count within N% of prior day                   | 30%             |
| uniqueness           | ODS   | gme_ods_yahoo_spot        | (symbol, trade_date) has no duplicates              | 0 duplicates    |
| uniqueness           | ODS   | gme_ods_yahoo_options     | (contract_symbol, trade_date) has no duplicates     | 0 duplicates    |
| accepted_ranges      | DWD   | gme_dwd_options_daily     | implied_volatility BETWEEN 0 AND 20; strike > 0    | 0 failures      |
| business_reconciliation | ADS | gme_ads_daily_summary    | iv_rank BETWEEN 0 AND 1; pc_ratio > 0              | 0 failures      |

---

## T-19: Test Case

| Test ID | Layer | Table                     | Test Type       | Description                                          | Expected Result |
|---------|-------|---------------------------|-----------------|------------------------------------------------------|-----------------|
| TC-01   | ODS   | gme_ods_yahoo_spot        | unique          | PK uniqueness: (symbol, trade_date)                  | 0 failures      |
| TC-02   | ODS   | gme_ods_yahoo_spot        | not_null        | close, volume are non-null                           | 0 failures      |
| TC-03   | ODS   | gme_ods_yahoo_options     | unique          | PK uniqueness: (contract_symbol, trade_date)         | 0 failures      |
| TC-04   | ODS   | gme_ods_yahoo_options     | not_null        | strike, open_interest, implied_volatility non-null   | 0 failures      |
| TC-05   | DWD   | gme_dwd_options_daily     | relationships   | expiration_date FK resolves to dim_expiration         | 0 failures      |
| TC-06   | DWD   | gme_dwd_options_daily     | relationships   | trade_date FK resolves to dim_date                   | 0 failures      |
| TC-07   | DWD   | gme_dwd_options_daily     | accepted_values | option_type IN ('call', 'put')                       | 0 failures      |
| TC-08   | DWS   | gme_dws_expiry_daily      | not_null        | max_pain_strike, pc_ratio are non-null               | 0 failures      |
| TC-09   | ADS   | gme_ads_daily_summary     | accepted_values | iv_rank BETWEEN 0 AND 1 (or NULL if < 2 data points) | 0 failures     |
| TC-10   | ADS   | gme_ads_daily_summary     | not_null        | spot_close, iv30, hv20, net_gex, pc_ratio_total non-null | 0 failures  |

---

## T-20: Job Monitoring and Alerts

| Job Name             | Schedule           | SLA          | Alert Channel | Escalation                    |
|----------------------|--------------------|--------------|---------------|-------------------------------|
| daily_spot_ingest    | cron 0 21 * * 1-5  | T+2 hours    | pipeline_log  | Retry once, then notify owner |
| daily_options_ingest | cron 5 21 * * 1-5  | T+2 hours    | pipeline_log  | Retry once, then notify owner |
| daily_dbt_run        | cron 15 21 * * 1-5 | T+30 min     | pipeline_log  | Notify owner immediately      |
| dqc_checks           | post-dbt-run       | T+15 min     | pipeline_log  | Notify owner immediately      |

---

## T-21: Notable / Known Limitations

| ID   | Limitation Description                                                                 | Impact                                          | Mitigation                                      |
|------|----------------------------------------------------------------------------------------|------------------------------------------------|------------------------------------------------|
| L-1  | Yahoo Finance provides 15-minute delayed data; end-of-day pipeline only.               | No intraday signal capability.                  | Accept for daily-grain mart; label timestamps.  |
| L-2  | Greeks (gamma) must be derived via Black-Scholes; not natively available.               | Computation adds complexity; gamma accuracy depends on model assumptions. | Use standard Black-Scholes with explicitly documented assumptions (risk-free rate, no dividends). |
| L-3  | IV Rank requires 252 trading days of IV30 history for full accuracy.                   | First-year values use shorter lookback.          | Display lookback window count; label as provisional until threshold. |
| L-4  | Risk-free rate must be seeded externally.                                               | GEX values shift slightly with rate changes.     | Use US 10-year Treasury yield seed; refresh monthly. [THEORETICAL] |
| L-5  | No historical options chain data via Yahoo Finance; only current-day snapshot.          | Cannot backfill historical GEX, max pain, P/C.   | Pipeline accumulates forward from first run date. |
| L-6  | Max pain calculation uses brute-force cross-join across all strikes; O(S^2) per expiration. | Performance scales quadratically with strike count. | GME typically has < 50 strikes per expiration; acceptable at current scale. |

> Items L-1 through L-5 carried forward from BRD B-4. L-6 is a new technical limitation.

---

## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | mart-forge Conformance Examiner | 2026-05-27 | PHASE-G-CP1-AUTOGRADE |
| Data Engineer | mart-forge Phase G Agent | 2026-05-27 | PHASE-G-CP1-AUTOGRADE |
