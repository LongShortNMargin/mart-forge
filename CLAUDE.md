# mart-forge — Agent Session Rules

## Identity

This is **mart-forge**, a methodology-first framework for scaffolding Kimball data warehouses with agent assistance.

## Lifecycle Gates (Hard Rules)

1. **No TDD without a signed-off BRD.** The `mart-tdd` skill will refuse to generate a TDD unless a BRD exists and has been explicitly signed off by the operator.
2. **No scaffold without a signed-off TDD.** The `mart-bootstrap` skill will refuse to scaffold unless a TDD exists and has been explicitly signed off.
3. **No `mart.yml` before source discovery.** Source discovery, BRD, and TDD precede `mart.yml` generation. The bootstrap skill requires a signed BRD before generating `mart.yml`.

## Metric Rules

- Every metric must declare `source_type` (`native` | `derived` | `hybrid`) and `link_status` (`exact` | `proxy` | `unsupported` | `unverified`).
- Native metrics are pass-through only — no computation in the transform layer.
- Derived metrics must have explicit SQL/formula in the TDD `calculation` column. No placeholders like "derived", "computed", or "see model".
- Hybrid metrics require reconciliation rules documenting which component is native vs derived.
- Proxy links are advisory context only — never ingestion provenance or DQC truth.

## Physical Design Standard

Every table in a TDD must have a column-level spec with 6 fields:
```
column_name | data_type | definition | example_value | calculation | data_source
```

The `calculation` column must contain actual SQL/formula for derived columns and field mapping for native columns.

## ODS Contract

Every ODS table must define: source, grain, logical partition column, incremental strategy (valid dbt-duckdb strategy), unique_key, backfill method, restatement behavior, and provenance columns.

Idempotence: running the same partition twice must produce identical output.

## DQC Requirements

- All 8 control classes from the control catalog must be addressed per mart.
- Controls not applicable to a table/metric require a `not_applicable` entry with rationale.
- The `dqc_scorecard.json` must be mechanically generated from `dbt test` results — never hand-edited.
- Before marking any control `unsupported`/`exhausted`, enumerate and attempt all available resources with documented evidence.

## Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| ODS | `{prefix}_ods_{source}_{entity}` | `ord_ods_csv_orders` |
| DIM | `{prefix}_dim_{entity}` | `ord_dim_customer` |
| DWD | `{prefix}_dwd_{grain}_{entity}_di` | `ord_dwd_daily_order_line_di` |
| DWS | `{prefix}_dws_{dims}_{metric}_{window}` | `ord_dws_daily_revenue_1d` |
| ADS | `{prefix}_ads_{consumer}_{purpose}` | `ord_ads_executive_dashboard` |

Window suffixes: `_1d` (daily), `_nd` (rolling), `_td` (to-date), `_mtd` (month-to-date).

## Confidentiality

This repository must contain zero private paths, zero proprietary source identifiers, zero operator holdings/strategies, and zero internal project identities. All content must be suitable for open-source publication.

## Session Bootstrap

On session start, the `using-mart-forge` hook detects the current lifecycle phase and routes to the appropriate skill. Check: Does a BRD exist? Is it signed off? Does a TDD exist? Is it signed off?
