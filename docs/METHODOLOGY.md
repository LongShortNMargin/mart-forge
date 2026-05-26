# Kimball 4-Tier Methodology Reference

## Overview

mart-forge implements a Kimball-inspired dimensional modeling methodology organized
into a strict 5-layer pipeline. Each layer has a single responsibility, a defined
grain contract, and explicit dependency rules. Data flows forward only — no layer
may reference a layer downstream of itself.

## Layer Architecture

```
  ┌─────────────┐
  │   Sources    │   External APIs, files, databases
  └──────┬──────┘
         │  extract (incremental / full)
         ▼
  ┌─────────────┐
  │     ODS     │   Operational Data Store — raw ingestion
  └──────┬──────┘
         │  conform keys, deduplicate
         ├──────────────────┐
         ▼                  ▼
  ┌─────────────┐    ┌─────────────┐
  │     DIM     │    │     DWD     │   Dimension + Detail/Fact
  └──────┬──────┘    └──────┬──────┘
         │                  │
         │    ┌─────────────┘
         │    │  aggregate, window
         ▼    ▼
  ┌─────────────┐
  │     DWS     │   Summary — rollups & KPIs
  └──────┬──────┘
         │  join DWS + DIM
         ▼
  ┌─────────────┐
  │     ADS     │   Application Data Store — presentation tables
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Dashboard  │   BI tools, notebooks, exports
  └─────────────┘
```

## Layer Definitions

### ODS — Operational Data Store

**Purpose:** Raw ingestion layer. Preserves the source system grain exactly as
received, with minimal transformation.

**Rules:**
- One ODS model per source endpoint or file.
- Incremental materialization preferred (`merge` on business key + timestamp).
- Add provenance columns: `provider`, `pull_ts_utc`, `run_id`.
- No business logic, no joins, no aggregations.
- Column names may be renamed to snake_case but values are never altered.
- Grain: one row = one record as delivered by the source system.

### DIM — Dimension

**Purpose:** Conformed dimensions shared across fact tables. Provide human-readable
descriptive attributes and surrogate keys.

**Rules:**
- Surrogate key column: `{entity}_sk` (integer, auto-generated).
- Business key column: `{entity}_bk` or natural composite key.
- Seed-backed dimensions use dbt seeds for static reference data.
- SCD Type 2 when history tracking is required (`valid_from`, `valid_to`, `is_current`).
- No measures or metrics — dimensions are descriptive only.
- Grain: one row = one entity instance (or one version for SCD2).

### DWD — Detail / Fact

**Purpose:** Cleaned fact records with business keys resolved. Contains both native
pass-through metrics and derived calculations.

**Rules:**
- Joins ODS to DIM to resolve surrogate keys.
- Native columns: passed through from ODS with no calculation (tagged `source_type: native`).
- Derived columns: explicit SQL expressions documented in mart.yml (tagged `source_type: derived`).
- Business keys replace raw source identifiers.
- Grain: one row = one business event at the declared grain (e.g., one trade, one daily price).

### DWS — Summary

**Purpose:** Aggregations, rollups, and window-function KPIs built from DWD facts.

**Subtypes:**

| Subtype          | Purpose                                  | Examples                              |
|------------------|------------------------------------------|---------------------------------------|
| **Count DWS**    | Row counts, event counts, cardinality    | trade_count, active_days, unique_instruments |
| **Performance DWS** | Rates, averages, percentiles, ratios | avg_spread, win_rate_pct, p95_latency |

**Rules:**
- Always references DWD (never ODS directly).
- GROUP BY must align with the declared grain.
- Window functions are permitted for running totals, rankings, moving averages.
- Every metric must trace back to a DWD column or an explicit SQL expression.
- Grain: one row = one aggregation bucket (e.g., one instrument per day).

### ADS — Application Data Store

**Purpose:** Presentation-ready "one-big-table" views that join DWS summaries with
DIM attributes for direct dashboard consumption.

**Rules:**
- Joins DWS + DIM only — no raw ODS or DWD references.
- Denormalized: all attributes the dashboard needs in a single SELECT.
- May include calculated display columns (formatted strings, conditional labels).
- No further aggregation — ADS is the final shape.
- Grain: matches the DWS grain, enriched with dimension attributes.

## Grain Rules

Every model in mart-forge must declare its grain explicitly in the model's
`mart.yml` configuration:

```yaml
grain: one row per instrument per trading day
```

Grain violations are caught by DQC controls (duplicate detection, PK integrity).
A model that cannot state its grain in a single sentence is not ready for implementation.

## Layer Dependency Matrix

| Layer | May Reference         | Must Not Reference |
|-------|-----------------------|--------------------|
| ODS   | Source (external)     | DIM, DWD, DWS, ADS |
| DIM   | ODS, Seeds            | DWD, DWS, ADS      |
| DWD   | ODS, DIM              | DWS, ADS           |
| DWS   | DWD, DIM              | ODS, ADS           |
| ADS   | DWS, DIM              | ODS, DWD           |

## Materialization Defaults

| Layer | Default Materialization | Override Allowed |
|-------|------------------------|------------------|
| ODS   | incremental (merge)    | table            |
| DIM   | table                  | incremental      |
| DWD   | incremental (merge)    | table            |
| DWS   | table                  | incremental      |
| ADS   | table                  | view             |

## Lifecycle Integration

The methodology layers map directly to the mart-forge skill lifecycle:

1. `/source-discovery` identifies providers and metrics (feeds ODS design).
2. `/mart-brd` captures business requirements (defines DWD/DWS metrics).
3. `/mart-tdd` produces the technical design (specifies all layers + grain).
4. `/mart-bootstrap` scaffolds the dbt models per layer.
5. `/mart-dqc` validates each layer against the 8-control quality catalog.
6. `/mart-review` audits the complete pipeline end-to-end.
