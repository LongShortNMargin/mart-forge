# Technical Design Document — {Mart Name}

**Status:** Draft
**Version:** 0.1
**Date:** {YYYY-MM-DD}
**Author:** {author}
**Reviewer:** {reviewer}
**BRD Reference:** {link to signed BRD}
**Grade:** Pending

---

## T-1. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | {YYYY-MM-DD} | {author} | Initial draft |

---

## T-2. Design Reasoning

### Step 1: Select Business Process

{What operational activity generates the measurable events? Trace to BRD B-2.}

### Step 2: Declare the Grain

{What does one row in the primary fact table represent? This is the most critical design decision.}

**Grain statement:** One row = {grain definition}

### Step 3: Identify Dimensions

{What descriptive context applies to each fact row?}

| Dimension | Description | SCD Type | Seed-Backed |
|-----------|-------------|----------|-------------|
| dim_date | Calendar with business day flags | Type 0 | Yes |
| {dim_name} | {description} | Type 0/1/2 | Yes/No |

### Step 4: Identify Facts

{What numeric, additive measurements does the business need?}

| Fact | Source Type | Grain | Additivity |
|------|-------------|-------|-----------|
| {fact} | native/derived/hybrid | {grain} | additive/semi-additive/non-additive |

---

## T-3. Table Summary

{All required table types listed with purpose and grain. Every entry MUST trace forward to T-5 and T-12.}

| Table Name | Layer | Purpose | Grain | Materialization |
|------------|-------|---------|-------|-----------------|
| {prefix}_ods_{source}_{entity} | ODS | Raw ingestion | {grain} | incremental |
| {prefix}_dim_{entity} | DIM | {purpose} | {grain} | table |
| {prefix}_dwd_{grain}_{entity}_di | DWD | {purpose} | {grain} | incremental |
| {prefix}_dws_{dims}_{metric}_{window} | DWS | {purpose} | {grain} | table |
| {prefix}_ads_{consumer}_{purpose} | ADS | {purpose} | {grain} | table |

**Table type coverage:**
- [ ] ODS — required / not_applicable (rationale: ___)
- [ ] DIM — required / not_applicable (rationale: ___)
- [ ] DWD — required / not_applicable (rationale: ___)
- [ ] DWS — required / not_applicable (rationale: ___)
- [ ] ADS — required / not_applicable (rationale: ___)

---

## T-4. Data Architecture Diagram

```
Source(s)
    │
    ▼
┌─────────┐
│   ODS   │  Raw ingestion with provenance
└────┬────┘
     │
     ▼
┌─────────┐     ┌─────────┐
│   DWD   │◄────│   DIM   │  Conformed dimensions (seed-backed)
└────┬────┘     └─────────┘
     │
     ▼
┌─────────┐
│   DWS   │  Aggregations and rollups
└────┬────┘
     │
     ▼
┌─────────┐
│   ADS   │  Application-facing OBTs
└─────────┘
     │
     ▼
  Dashboard
```

---

## T-5. Column Specification

{Column-level spec per table. Every column has all 6 fields.}

### {Table Name}

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| {col} | {type} | {definition} | {example} | {SQL/formula or field mapping} | {source} |

**calculation column rules:**
- Native columns: field mapping notation (e.g., `source.field_name → pass-through`)
- Derived columns: actual SQL/formula (e.g., `price * quantity`)
- No placeholders: "derived", "computed", "see model" are forbidden

---

## T-6. ODS Table Design

{Per-table specification with all required fields from the ODS contract.}

### {prefix}_ods_{source}_{entity}

| Field | Value |
|-------|-------|
| Source | {provider + endpoint/method} |
| Grain | {what one row represents} |
| Logical Partition | {column for incremental windowing} |
| Incremental Strategy | {valid dbt-duckdb strategy, e.g., delete+insert} |
| Unique Key | {deduplication composite, e.g., ['date', 'id']} |
| Backfill | {how to load historical data} |
| Restatement | {behavior when source corrects data} |
| Provenance Columns | provider, pull_ts_utc, quote_ts_utc, run_id |

**Idempotence:** Running the same partition twice produces identical output. CI includes rerun test.

---

## T-7. Dimension Table Design

{Conformed dimensions with SCD strategy. Each dimension gets the full column spec.}

### {prefix}_dim_{entity}

**Design properties:**

| Property | Value |
|----------|-------|
| Grain | One row = one {entity} |
| SCD Strategy | Type 0 (immutable) / Type 1 (overwrite) / Type 2 (history) |
| Seed-Backed | Yes / No |
| Unknown Member | Row with surrogate key = -1, all attributes = 'Unknown' |

**Column specification (6-column format):**

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| {entity}_sk | INTEGER | Surrogate key | 1 | row_number() over (order by {entity}_id) | Generated |
| {entity}_id | VARCHAR | Natural key from source | 'ENT-001' | source.entity_id -> pass-through | {source} |
| {entity}_name | VARCHAR | Descriptive name | 'Example Entity' | source.name -> pass-through | {source} |
| effective_from | DATE | SCD2: validity start (if Type 2) | '2026-01-01' | Type 2 merge logic | Generated |
| effective_to | DATE | SCD2: validity end (if Type 2) | '9999-12-31' | Type 2 merge logic | Generated |
| is_current | BOOLEAN | SCD2: current row flag (if Type 2) | true | Type 2 merge logic | Generated |

{Repeat the full column specification table for each dimension table in the design.}
{If this table type is not required, provide a signed not_applicable rationale below.}

**not_applicable rationale (if this table type is not required):**
{Rationale with sign-off stamp, e.g.: "No conformed dimensions required because..." [SIGN-OFF STAMP]}

---

## T-8. Fact Table Design (DWD)

{Cleaned facts with business keys. Every metric-bearing column requires source_type classification.}

### {prefix}_dwd_{grain}_{entity}_di

**Design properties:**

| Property | Value |
|----------|-------|
| Grain | One row = {grain definition} |
| Incremental Strategy | delete+insert |
| Unique Key | {composite key columns} |
| Upstream | {prefix}_ods_{source}_{entity} |

**Column specification (6-column format) — source_type required for metric columns:**

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| fact_sk | VARCHAR | Surrogate key (hash) | 'a1b2c3...' | md5(record_id \|\| pull_date) | Generated |
| date_key | INTEGER | FK to dim_date | 1 | dim_date.date_sk via join on pull_date | dim_date |
| {entity}_key | INTEGER | FK to dim_{entity} | 1 | coalesce(dim.{entity}_sk, -1) | dim_{entity} |
| {native_metric} | DECIMAL | {definition} [source_type: native] | 10.50 | source.field_name -> pass-through | ODS |
| {derived_metric} | DECIMAL | {definition} [source_type: derived] | 105.00 | {actual SQL: field_a * field_b} | Computed |
| {hybrid_metric} | DECIMAL | {definition} [source_type: hybrid] | 50.25 | {actual SQL + reconciliation rule} | ODS + Computed |
| provider | VARCHAR | Source identifier [provenance] | 'provider_name' | source.provider -> pass-through | ODS |
| pull_ts_utc | TIMESTAMP | Ingestion timestamp [provenance] | '2026-01-01T06:00:00Z' | source.pull_ts_utc -> pass-through | ODS |
| quote_ts_utc | TIMESTAMP | Source data timestamp [provenance] | '2026-01-01T05:30:00Z' | source.quote_ts_utc -> pass-through | ODS |
| run_id | VARCHAR | Pipeline run trace [provenance] | 'uuid-here' | source.run_id -> pass-through | ODS |

{Repeat the full column specification table for each DWD fact table.}
{If this table type is not required, provide a signed not_applicable rationale below.}

**not_applicable rationale (if this table type is not required):**
{Rationale with sign-off stamp}

---

## T-9. Count Aggregation Design (DWS)

{Count-type DWS tables. Every aggregation column requires explicit SQL and source_type (typically derived).}

### {prefix}_dws_{dims}_{metric}_{window}

**Design properties:**

| Property | Value |
|----------|-------|
| Grain | One row = {aggregation grain} |
| Window | {_1d / _nd / _td / _mtd} |
| Materialization | table (full rebuild) |
| Upstream | {prefix}_dwd_{grain}_{entity}_di |

**Column specification (6-column format):**

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| date_key | INTEGER | FK to dim_date | 1 | source.date_key -> pass-through | DWD |
| {count_metric} | BIGINT | {definition} [source_type: derived] | 150 | COUNT(DISTINCT {entity}_key) | DWD aggregation |
| {sum_metric} | DECIMAL | {definition} [source_type: derived] | 5000.00 | SUM({metric_column}) | DWD aggregation |
| calculated_at | TIMESTAMP | Aggregation timestamp | '2026-01-01T06:05:00Z' | current_timestamp | Generated |

{Repeat for each count-type DWS table.}
{If this table type is not required, provide a signed not_applicable rationale below.}

**not_applicable rationale (if this table type is not required):**
{Rationale with sign-off stamp}

---

## T-10. Performance Aggregation Design (DWS)

{Performance/ratio DWS tables. Every ratio column requires explicit SQL and source_type classification.}

### {prefix}_dws_{dims}_{metric}_{window}

**Design properties:**

| Property | Value |
|----------|-------|
| Grain | One row = {aggregation grain} |
| Window | {_1d / _nd / _td / _mtd} |
| Materialization | table (full rebuild) |
| Upstream | {prefix}_dwd_{grain}_{entity}_di |

**Column specification (6-column format):**

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| date_key | INTEGER | FK to dim_date | 1 | source.date_key -> pass-through | DWD |
| {ratio_metric} | DECIMAL | {definition} [source_type: derived] | 0.75 | SUM(numerator) / NULLIF(SUM(denominator), 0) | DWD aggregation |
| {avg_metric} | DECIMAL | {definition} [source_type: derived] | 42.50 | AVG({metric_column}) | DWD aggregation |
| {window_metric} | DECIMAL | {definition} [source_type: derived] | 38.20 | AVG({col}) OVER (ORDER BY date_key ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) | DWD window |
| calculated_at | TIMESTAMP | Aggregation timestamp | '2026-01-01T06:05:00Z' | current_timestamp | Generated |

{Repeat for each performance-type DWS table.}
{If this table type is not required, provide a signed not_applicable rationale below.}

**not_applicable rationale (if this table type is not required):**
{Rationale with sign-off stamp}

---

## T-11. Presentation Table Design (ADS)

{Application-facing OBTs. Every column must trace to an upstream DWS/DWD model and to a BRD metric.}

### {prefix}_ads_{consumer}_{purpose}

**Design properties:**

| Property | Value |
|----------|-------|
| Grain | One row = {presentation grain} |
| Materialization | table (full rebuild) |
| Consumer | {who/what consumes this table} |
| Upstream | {prefix}_dws_* and {prefix}_dim_* |

**Column specification (6-column format) with traceability:**

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|------------|-------------|
| calendar_date | DATE | Date context | '2026-01-15' | dim_date.calendar_date via join | dim_date |
| {entity}_name | VARCHAR | Entity descriptor | 'Example' | dim_{entity}.{entity}_name via join | dim_{entity} |
| {metric_1} | DECIMAL | {definition} — traces to BRD M-{N} | 150.00 | dws_{model}.{metric_column} via join | DWS |
| {metric_2} | DECIMAL | {definition} — traces to BRD M-{N} | 0.75 | dws_{model}.{ratio_column} via join | DWS |
| calculated_at | TIMESTAMP | Last aggregation time | '2026-01-01T06:05:00Z' | dws_{model}.calculated_at via join | DWS |

**Metric traceability matrix:**

| ADS Column | Upstream Model.Column | BRD Metric | Link Status |
|------------|----------------------|------------|-------------|
| {metric_1} | {dws_model}.{column} | M-{N} | exact/proxy/unsupported |

{Repeat for each ADS table.}
{If this table type is not required, provide a signed not_applicable rationale below.}

**not_applicable rationale (if this table type is not required):**
{Rationale with sign-off stamp}

---

## T-12. Physical Design

{Column-level spec for every table type. Must cover all tables in T-3.}

{Repeat T-5 format for each table, ensuring every table from Table Summary has an entry.}

---

## T-13. Implementation Specification

### dbt Model Configuration

| Setting | Value |
|---------|-------|
| Naming convention | `{prefix}_{layer}_{entity}` |
| Materialization (ODS/DWD) | incremental |
| Materialization (DIM/DWS/ADS) | table |
| ref() chain | ODS → DWD → DWS → ADS; DIM referenced by DWD |
| Jinja patterns | `{{ var('partition_date') }}` for backfill |
| Macro usage | {list any custom macros} |

---

## T-14. DQC Plan

{Controls per the 8-class control catalog with applicability.}

| Control Class | Applicable Tables | Severity | Source Type Scope | Status |
|---------------|-------------------|----------|-------------------|--------|
| PK Integrity | All | error | All | Required |
| FK Integrity | DWD, DWS, ADS | error | All | Required |
| Freshness | ODS, DWD | error | All | Required |
| Completeness | All with refresh | warn | All | Required |
| Accepted Ranges | Numeric metrics | warn | native, derived | Required |
| Duplicate Detection | DWD facts | error | All | Required |
| Null-Rate | All | warn | All | Required |
| Business Reconciliation | Key metrics | error/warn | When exact comparator exists | {Required/not_applicable} |

**not_applicable entries:**

| Control | Table/Metric | Rationale |
|---------|-------------|-----------|
| {control} | {table} | {why it does not apply} |

---

## T-15. Test Inventory

| Test Name | Type | Target Model | Expected Result |
|-----------|------|-------------|-----------------|
| {test_name} | generic/singular/reconciliation | {model} | {expected} |

---

## T-16. Operations

| Setting | Value |
|---------|-------|
| Refresh Schedule | {cron expression} |
| SLA | {max acceptable delay} |
| Timezone | {timezone} |
| Holiday Handling | {skip/run with empty check} |
| Alerting | {channels/method} |
| Failure Handling | {retry strategy} |

---

## T-17. Known Limitations

### Declared Constraints

{Technical limitations of the current design.}

### Unsupported Metrics

{Metrics without external verification. Resource exhaustion evidence required.}

| Metric | Status | Attempts | Evidence |
|--------|--------|----------|----------|
| {metric} | unsupported | {N} | {evidence} |

### Known Data Gaps

{What data gaps exist and their impact.}

---

## Dashboard Specification

{Visualization list with chart type, data source, and link_status display rules.}

| # | Visualization | Chart Type | Data Source Model | Metrics | Link Status Display |
|---|---------------|-----------|-------------------|---------|---------------------|
| V-1 | {title} | {line/bar/table/card} | {model} | {metrics} | {per link_status rules} |

**Link-status display rules:**
- `exact`: Verification link icon → "Exact verification source"
- `proxy`: Advisory link, distinguished → "Advisory comparator (proxy)"
- `unsupported`: No link → "No external comparator available"

---

## Fixture Manifest (if applicable)

| Field | Value |
|-------|-------|
| Source Date | {date} |
| Source Provider | {provider} |
| Captured Value | {description} |
| Row Count | {N} |
| Schema Hash | {hash} |

---

*TDD Grade: {Pending/A/B/C/D/F} — Assigned by reviewer.*
*Sign-off required before proceeding to scaffold.*
