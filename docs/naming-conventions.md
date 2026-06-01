# Naming Conventions

Names in a mart-forge warehouse encode the layer and the role. A reader
who knows the conventions can guess a model's purpose from its name
alone.

## Models

```
<prefix>_<layer>_<noun>[_<grain>]
```

| Layer | Prefix? | Example |
|-------|---------|---------|
| ODS | yes | `gme_ods_cboe_options_chain` |
| DIM | no  | `dim_date`, `dim_instrument`  (conformed, prefix-free) |
| DWD | yes | `gme_dwd_option_contract_di` |
| DWS | yes | `gme_dws_strike_gex_1d`, `gme_dws_daily_snapshot_1d` |
| ADS | yes | `gme_ads_market_dashboard` |

Rules:

- `<prefix>` is the mart's three-to-four-letter code (e.g., `gme`,
  `orders`). It is declared once in `mart.yml`.
- `<layer>` is one of `ods`, `dim`, `dwd`, `dws`, `ads`.
- `<noun>` describes the entity (`option_contract`, `customer`,
  `pricing_event`).
- `<grain>` is optional but recommended on DWD and DWS: `_di` for daily
  incremental, `_1d` for one-day rollup, `_1h` for hourly.
- Dimensions are NOT prefixed because they are conformed across marts
  in the same warehouse.

## Columns

| Use | Convention |
|-----|-----------|
| Primary key surrogate | `<entity>_sk` (e.g., `option_contract_sk`) |
| Business key | `<entity>_id` or `<entity>_code` |
| Foreign key | `<dimension>_sk` (matching the dim's PK) |
| Timestamps in UTC | `<event>_ts_utc` (e.g., `pull_ts_utc`, `quote_ts_utc`) |
| Dates | `<event>_date` |
| Counts | `<noun>_count` |
| Amounts (monetary) | `<noun>_amt_<currency>` (e.g., `revenue_amt_usd`) |
| Rates / percentages | `<noun>_pct` or `<noun>_rate` |
| Booleans | `is_<adjective>` or `has_<noun>` |
| Provenance | `provider`, `pull_ts_utc`, `run_id` (mandatory on ODS) |

## Files

| Artifact | Path |
|----------|------|
| Mart manifest | `mart.yml` (one per mart) |
| BRD | `docs/business-requirements.md` |
| TDD | `docs/tech-design-doc.md` |
| Source catalog | `docs/source_catalog.json` |
| DQC scorecard | `dqc_scorecard.json` |
| Coverage manifest | `coverage_manifest.json` |
| Skill invocations | `.skill-invocations.jsonl` |
| dbt models | `models/<layer>/<model_name>.sql` |
| dbt schema | `models/<layer>/schema.yml` |
| Seeds | `seeds/<seed_name>.csv` |
| Singular tests | `tests/<test_name>.sql` |
| Dashboard | `dashboard/app.py` |
| CI workflow | `.github/workflows/daily.yml` |

## What not to do

- **Don't shorten unnecessarily.** `gme_ods_opt_chain` saves four
  characters and forces the reader to expand `opt`. Use the full word.
- **Don't add the warehouse name.** The whole repository is a
  warehouse; prefixing every model with `warehouse_` is redundant.
- **Don't encode the source in the noun.** Source identity is captured
  in the ODS contract; encoding it again in the model name (e.g.,
  `dwd_yfinance_option_contract`) creates renames on every provider
  swap.

## Referenced from

- `SPEC.md` §T-16 (Coding).
- `templates/models/*/template.sql`.
- `scripts/lint_layer_direction.py` (uses the layer prefix to detect
  direction).
