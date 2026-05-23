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

{Conformed dimensions with SCD strategy.}

### {prefix}_dim_{entity}

| Attribute | SCD Type | Seed-Backed | Notes |
|-----------|----------|-------------|-------|
| {attribute} | Type 0/1/2 | Yes/No | {notes} |

**Unknown member:** Row with surrogate key = -1, all attributes = 'Unknown'.

---

## T-8. Fact Table Design (DWD)

{Cleaned facts with business keys and source_type classification.}

### {prefix}_dwd_{grain}_{entity}_di

| Column | Source Type | Calculation | Notes |
|--------|------------|-------------|-------|
| {metric_column} | native/derived/hybrid | {SQL or field mapping} | {notes} |

---

## T-9. Count Aggregation Design (DWS)

{Count-type aggregations with explicit SQL.}

### {prefix}_dws_{dims}_{metric}_{window}

| Metric | Source Type | Calculation (SQL) |
|--------|------------|-------------------|
| {count_metric} | derived | {explicit SQL, e.g., COUNT(DISTINCT entity_id)} |

---

## T-10. Performance Aggregation Design (DWS)

{Performance/ratio aggregations with explicit SQL.}

### {prefix}_dws_{dims}_{metric}_{window}

| Metric | Source Type | Calculation (SQL) |
|--------|------------|-------------------|
| {ratio_metric} | derived | {explicit SQL, e.g., SUM(x) / NULLIF(SUM(y), 0)} |

---

## T-11. Presentation Table Design (ADS)

{Application-facing OBTs with metric-to-column traceability.}

### {prefix}_ads_{consumer}_{purpose}

| Column | Upstream Source | Traceability |
|--------|---------------|-------------|
| {column} | {dws/dwd model}.{column} | BRD metric M-{N} |

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
