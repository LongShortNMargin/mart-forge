# Naming Conventions

## Model Naming

All model names follow: `{prefix}_{layer}_{descriptive_name}`

| Layer | Pattern | Example |
|-------|---------|---------|
| ODS | `{prefix}_ods_{source}_{entity}` | `ord_ods_csv_orders` |
| DIM | `{prefix}_dim_{entity}` | `ord_dim_customer` |
| DWD | `{prefix}_dwd_{grain}_{entity}_di` | `ord_dwd_daily_order_line_di` |
| DWS | `{prefix}_dws_{dims}_{metric}_{window}` | `ord_dws_daily_revenue_1d` |
| ADS | `{prefix}_ads_{consumer}_{purpose}` | `ord_ads_executive_dashboard` |

### Prefix

A short (2-4 character) identifier for the mart: `ord` (orders), `inv` (inventory), `usr` (users).

### Window Suffixes

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_1d` | Daily snapshot | `dws_daily_snapshot_1d` |
| `_nd` | N-day rolling window | `dws_trend_nd` |
| `_td` | To-date accumulating | `dws_lifecycle_td` |
| `_mtd` | Month-to-date | `dws_volume_mtd` |

### Fact Table Suffix

All fact tables (DWD layer) end with `_di` (daily incremental).

## Column Naming

- All columns use `snake_case`
- Surrogate keys: `{entity}_sk`
- Natural keys: `{entity}_id` or `{entity}_code`
- Date foreign keys: `{role}_date_key` (role-playing FK to dim_date)
- Provenance: `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id`
- SCD Type 2: `effective_from`, `effective_to`, `is_current`
- Boolean: `is_{attribute}` or `has_{attribute}`
- Counts: `{entity}_count`
- Amounts: `{metric}_amount` or `total_{metric}`
- Ratios: `{metric}_ratio` or `{metric}_pct`

## Test Naming

- Generic tests: use dbt built-in names (`not_null`, `unique`, `relationships`, `accepted_values`)
- Singular tests: `test_{model}_{what_it_checks}`
  - Example: `test_dwd_orders_no_future_dates`
  - Example: `test_ods_freshness_within_sla`
  - Example: `test_dws_revenue_positive`

## File Organization

```
models/
├── ods/           # One file per source entity
├── dim/           # One file per dimension
├── dwd/           # One file per fact grain
├── dws/           # One file per aggregation
└── ads/           # One file per consumer application
seeds/             # Static CSVs (dim_date, dim_instrument)
tests/             # Singular test SQL files
```

## Database Naming

- Database: `{mart_name}_db` (e.g., `orders_db`)
- Schema: `main` (default for DuckDB)
- Use `mart.yml` `db_name` field for configuration
