# Naming Conventions

## Overview

Consistent naming is a core principle of mart-forge. Every table, column, and file
follows deterministic patterns so that any contributor can locate or predict names
without checking documentation. These conventions are enforced by the `/mart-review`
skill and validated during CI.

## Table Naming

### Pattern

```
{prefix}_{layer}_{entity}_{grain}
```

| Segment   | Description                                      | Examples                    |
|-----------|--------------------------------------------------|-----------------------------|
| `prefix`  | Short mart identifier (2-4 chars)                | `gme`, `fin`, `ops`        |
| `layer`   | Methodology layer                                | `ods`, `dim`, `dwd`, `dws`, `ads` |
| `entity`  | Business entity or subject area                  | `instrument`, `options`, `trades` |
| `grain`   | Temporal or categorical grain suffix             | `daily`, `monthly`, `snapshot` |

### Examples

| Full Name                    | Layer | Entity      | Grain    |
|------------------------------|-------|-------------|----------|
| `gme_ods_options_daily`      | ODS   | options     | daily    |
| `gme_dim_instrument`         | DIM   | instrument  | (none)   |
| `gme_dwd_options_daily`      | DWD   | options     | daily    |
| `gme_dws_volume_daily`       | DWS   | volume      | daily    |
| `gme_ads_dashboard_daily`    | ADS   | dashboard   | daily    |

### Rules

- All lowercase, underscores only. No hyphens, no camelCase.
- DIM tables omit the grain suffix when the grain is "one row per entity."
- Grain suffix is mandatory for all fact-side tables (ODS, DWD, DWS, ADS).
- Prefix is defined once per mart in `mart.yml` and reused across all models.

## Column Naming

### General Rules

- `snake_case` everywhere. No abbreviations except the standard set below.
- Column names must be self-descriptive at the grain of the table.
- Boolean columns use `is_` or `has_` prefix: `is_current`, `has_dividends`.
- Percentage columns use `_pct` suffix: `win_rate_pct`, `null_rate_pct`.

### Standard Abbreviations

Only these abbreviations are permitted. All other words must be spelled out.

| Abbreviation | Meaning       |
|--------------|---------------|
| `id`         | identifier    |
| `sk`         | surrogate key |
| `bk`         | business key  |
| `ts`         | timestamp     |
| `utc`        | UTC timezone  |
| `pct`        | percentage    |
| `qty`        | quantity      |
| `amt`        | amount        |
| `avg`        | average       |
| `min`        | minimum       |
| `max`        | maximum       |
| `cnt`        | count         |
| `num`        | number        |

### Provenance Columns

Every ODS and DWD table must include these columns for lineage tracking:

| Column          | Type      | Description                                |
|-----------------|-----------|--------------------------------------------|
| `provider`      | VARCHAR   | Data source identifier (e.g., `yahoo_fin`) |
| `pull_ts_utc`   | TIMESTAMP | When the data was extracted from source     |
| `quote_ts_utc`  | TIMESTAMP | Source-reported timestamp of the data point |
| `run_id`        | VARCHAR   | dbt run identifier for traceability         |

### Key Columns

**Surrogate Keys:**
- Pattern: `{entity}_sk`
- Type: INTEGER, auto-incrementing or hash-based
- Examples: `instrument_sk`, `account_sk`, `strategy_sk`

**Business Keys:**
- Pattern: `{entity}_bk` for single-column keys
- For composite keys, use descriptive column names without the `_bk` suffix
- Examples: `instrument_bk`, or composite `(exchange, ticker, expiry_date)`

### Date and Time Columns

| Pattern              | Usage                                            |
|----------------------|--------------------------------------------------|
| `{event}_date`       | Calendar date without time: `trade_date`, `expiry_date` |
| `{event}_ts_utc`     | Full timestamp in UTC: `created_ts_utc`, `quote_ts_utc` |
| `valid_from`         | SCD2 effective start (TIMESTAMP)                 |
| `valid_to`           | SCD2 effective end (TIMESTAMP, NULL = current)   |

### Metric Columns

Metrics follow a `{measure}_{aggregation}` pattern when in DWS tables:

| Example               | Measure    | Aggregation |
|-----------------------|------------|-------------|
| `volume_sum`          | volume     | sum         |
| `spread_avg`          | spread     | avg         |
| `price_close`         | price      | close       |
| `return_pct`          | return     | pct         |

In DWD tables, metrics use their natural names without aggregation suffixes,
since DWD is at the event grain: `open_price`, `close_price`, `volume`, `bid`, `ask`.

## File Naming

### dbt Model Files

```
models/{layer}/{prefix}_{layer}_{entity}_{grain}.sql
```

### dbt Test Files

```
tests/{prefix}_{layer}_{entity}_{grain}_{control}.sql
```

### Seed Files

```
seeds/{prefix}_{entity}_seed.csv
```

### mart.yml Location

```
models/{layer}/mart.yml        (one per layer directory)
```

## Validation

The `/mart-review` skill checks naming conventions automatically during review.
Violations produce findings with severity `warn` and a suggested fix. The CI
pipeline can optionally enforce naming as a blocking gate via the
`naming_strict: true` flag in `mart.yml`.
