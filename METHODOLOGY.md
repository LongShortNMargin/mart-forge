# Kimball Methodology Reference

This document codifies the Kimball dimensional modeling methodology as applied by mart-forge. It serves as the authoritative reference for agents and data engineers using this framework.

---

## 1. Dimensional Modeling Principles

Dimensional modeling organizes data into **facts** (measurable events) and **dimensions** (descriptive context). The methodology optimizes for query performance and business comprehension over storage efficiency.

### 1.1 The Four-Step Design Process

Every mart design follows these steps in order:

1. **Select the business process** — Identify the operational activity that generates measurable events (e.g., order placement, session activity, trade execution).
2. **Declare the grain** — State what one row in the fact table represents. This is the most critical decision and must be explicit before any column design.
3. **Identify the dimensions** — Choose the descriptive context that applies to each fact row (who, what, where, when, how).
4. **Identify the facts** — Select the numeric, additive measurements that the business needs to analyze.

### 1.2 Grain Discipline

- Each fact table declares **exactly one grain** in its documentation.
- The grain must be derivable from the primary key composite.
- No multi-grain fact tables. If grains differ, split into separate models.
- All dimension foreign keys and facts must be true at the declared grain.

---

## 2. Data Layer Architecture

mart-forge uses a five-tier architecture extending the traditional Kimball model:

### 2.1 ODS (Operational Data Store)

**Purpose:** Raw ingestion layer. Data arrives here exactly as the source provides it, with provenance metadata added.

**Rules:**
- No business logic transformations
- Append-only with deduplication via `unique_key`
- Every row carries provenance columns: `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id`
- Incremental materialization with partition-based windowing
- Explicit column lists (no `SELECT *`)
- Idempotent: re-running the same partition produces identical output

**Required specification fields:**
| Field | Description |
|-------|------------|
| `source` | Provider + endpoint/method |
| `grain` | What one row represents |
| `logical_partition` | Column for incremental windowing |
| `incremental_strategy` | Valid dbt-duckdb strategy (e.g., `delete+insert`) |
| `unique_key` | Deduplication composite key |
| `backfill` | How to load historical data |
| `restatement` | Behavior when source data is corrected |
| `provenance_columns` | Audit trail fields |

### 2.2 DIM (Dimensions)

**Purpose:** Conformed descriptive context shared across fact tables.

**Rules:**
- Seed-backed where applicable (e.g., date calendar, instrument config)
- Every dimension includes an **unknown member** (surrogate key = -1, all attributes = 'Unknown')
- Facts with missing FK point to the unknown member, never NULL
- SCD strategy declared per dimension:
  - **Type 0:** Immutable attributes — no update logic
  - **Type 1:** Overwrite-safe attributes — simple UPDATE on natural key
  - **Type 2:** History-critical attributes — `effective_from`, `effective_to`, `is_current` columns
- Default is Type 1 unless explicitly declared Type 2
- Role-playing dimensions supported (e.g., `dim_date` as both `trade_date` and `expiry_date`)

### 2.3 DWD (Data Warehouse Detail)

**Purpose:** Cleaned facts with business keys. The primary analytical grain.

**Rules:**
- Business key deduplication from ODS
- Native fields: pass-through with field mapping (no computation)
- Derived fields: explicit SQL/formula in the `calculation` column
- Surrogate keys generated here, never exposed to consumers
- Natural keys preserved for lineage
- Incremental materialization

### 2.4 DWS (Data Warehouse Summary)

**Purpose:** Pre-computed aggregations, rollups, and window calculations.

**Rules:**
- Full rebuild (table materialization) — aggregation layer is cheap
- Window suffix conventions:
  - `_1d` — daily snapshot
  - `_nd` — N-day rolling window
  - `_td` — to-date accumulating
  - `_mtd` — month-to-date
- Every aggregation has explicit SQL in the `calculation` column
- Source_type classification: typically `derived` or `hybrid`

### 2.5 ADS (Application Data Store)

**Purpose:** Application-facing One Big Tables (OBTs) optimized for specific consumers.

**Rules:**
- Explicit column lists (no `SELECT *`)
- Metric-to-column traceability to upstream DWS/DWD
- Table materialization
- Consumer-specific: one ADS per dashboard/application

---

## 3. Bus Matrix

The bus matrix maps fact tables to shared (conformed) dimensions. Every mart must declare its bus matrix before implementation.

```
                    dim_date  dim_entity  dim_category
fact_event_di          X          X            X
fact_snapshot_di       X          X
```

**Rules:**
- Every dimension in the matrix must be a conformed dimension (shared definition)
- Every fact table must connect to `dim_date` at minimum
- Cross-mart conformed dimensions enable drill-across queries

---

## 4. Key Strategy

| Key Type | Where | Rule |
|----------|-------|------|
| Surrogate key | DWD fact PKs, DIM PKs | Integer or hash-based. Generated in DWD. Never exposed to consumers. |
| Natural key | ODS, DWD business keys | Source-system identifier. Preserved for lineage. |
| Unknown member | Every DIM | Row ID = -1. All attributes = 'Unknown'. Inserted via seed. |

---

## 5. Naming Conventions

### 5.1 Model Naming

| Layer | Pattern | Example |
|-------|---------|---------|
| ODS | `{prefix}_ods_{source}_{entity}` | `ord_ods_csv_orders` |
| DIM | `{prefix}_dim_{entity}` | `ord_dim_customer` |
| DWD | `{prefix}_dwd_{grain}_{entity}_di` | `ord_dwd_daily_order_line_di` |
| DWS | `{prefix}_dws_{dims}_{metric}_{window}` | `ord_dws_daily_revenue_1d` |
| ADS | `{prefix}_ads_{consumer}_{purpose}` | `ord_ads_executive_dashboard` |

### 5.2 Column Naming

- `snake_case` for all columns
- Surrogate keys: `{entity}_sk`
- Natural keys: `{entity}_id` or `{entity}_code`
- Date keys: `{role}_date_key` (role-playing FK to dim_date)
- Provenance: `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id`
- SCD Type 2: `effective_from`, `effective_to`, `is_current`

### 5.3 Test Naming

- Generic tests: use dbt built-in names (`not_null`, `unique`, `relationships`, `accepted_values`)
- Singular tests: `test_{model}_{what_it_checks}` (e.g., `test_dwd_orders_no_future_dates`)

---

## 6. Incremental Strategy

| Layer | Strategy | Rationale |
|-------|----------|-----------|
| ODS | Incremental, `unique_key` on PK | Append-only; no deletes |
| DWD | Incremental | Dedup + clean; idempotent re-runs |
| DWS/ADS | Full rebuild (table) | Aggregation layer is cheap |

### 6.1 Idempotency Contract

Re-running the same partition twice MUST produce identical output:
- No `current_timestamp()` in model logic (use `pull_ts_utc` from ODS)
- Incremental models use `unique_key` for deduplication
- Seeds are static CSVs, not dynamic queries
- CI MUST include a rerun idempotence test

---

## 7. Late-Arriving Data

| Scenario | Handling |
|----------|---------|
| Late-arriving fact | Insert with correct date; incremental model's `unique_key` handles idempotency. DWS rebuilds on next run. |
| Late-arriving dimension | Insert unknown-member row at fact load time. When dimension record arrives, Type 1 update fills attributes. |

---

## 8. Provenance

Every raw row must carry:

| Column | Type | Purpose |
|--------|------|---------|
| `provider` | string | Source identifier |
| `pull_ts_utc` | timestamp | When ingestion ran |
| `quote_ts_utc` | timestamp | Source data timestamp |
| `run_id` | string(UUID) | Pipeline run trace |

---

## 9. Physical Design Standard

Every table in a TDD must have a column-level spec with 6 fields:

```
column_name | data_type | definition | example_value | calculation | data_source
```

- `calculation` MUST contain actual SQL/formula for derived columns
- `calculation` MUST contain field mapping notation for native (pass-through) columns
- No "derived", "computed", or "see model" placeholders
- Bidirectional traceability: every generated SQL maps to a TDD field, every TDD metric maps to a model/test

---

## 10. Fixture and Live Mode

| Mode | Data Source | Display Rule |
|------|-----------|-------------|
| Fixture/demo | Static parquet/CSV with manifest | Dashboard shows "FIXTURE/DEMO" banner |
| Live | Production warehouse | Dashboard shows live data; "BLOCKED/STALE" if unavailable |

Fixture manifest must include: source date, source URL/provider, captured value, row count, schema hash.

Never silently substitute fixture for live data.
