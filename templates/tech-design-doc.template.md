# Technical Design Document: {mart_name}

> **Date:** {date}
> **Author:** {author}
> **Prefix:** {prefix}
> **Status:** Draft

---

## T-1: Changelog

| Version | Date       | Author   | Section(s) Changed | Summary of Changes |
|---------|------------|----------|---------------------|--------------------|
| 0.1     | {date}     | {author} | All                 | Initial draft      |

---

## T-2: Business Background

<!-- Reference the BRD for full context. Summarize the key business process and analytical purpose here. -->

_TODO: Brief recap of the business process, stakeholders, and analytical goals from the BRD._

---

## T-3: Metrics Breakdown

| Metric Name | Business Definition | source_type | link_status | Calculation Logic | Target Table |
|-------------|---------------------|-------------|-------------|-------------------|--------------|
|             |                     | native / derived / hybrid | exact / proxy / unsupported / unverified | | {prefix}_ads__ |

---

## T-4: Design Consideration (4-Step Kimball)

### Step 1: Select the Business Process

_TODO: Identify the operational process being modeled._

### Step 2: Declare the Grain

_TODO: Define the most atomic level of data stored in the fact table (e.g., one row per transaction per day)._

### Step 3: Identify the Dimensions

_TODO: List dimension tables and their role (e.g., dim_date for time-series slicing, dim_product for product attributes)._

### Step 4: Identify the Facts

_TODO: List the measurable, numeric facts captured at the declared grain._

---

## T-5: Bus Matrix

| Dimension / Fact Table | dim_date | dim_{entity_1} | dim_{entity_2} | {prefix}_dwd__ | {prefix}_dws__ |
|------------------------|----------|-----------------|-----------------|-----------------|-----------------|
| Business Process 1     | X        | X               |                 | X               | X               |

---

## T-6: Table Summary

| Layer | Table Name               | Materialization | Grain                | Description |
|-------|--------------------------|-----------------|----------------------|-------------|
| ODS   | {prefix}_ods__           | incremental     |                      |             |
| DIM   | dim_                     | table           |                      |             |
| DWD   | {prefix}_dwd__           | table           |                      |             |
| DWS   | {prefix}_dws__           | table           |                      |             |
| ADS   | {prefix}_ads__           | table           |                      |             |

---

## T-7: Data Architecture Diagram

```
Source Systems
    |
    v
[ ODS Layer ] -- raw ingestion, provenance columns
    |
    v
[ DIM Layer ] -- seed-backed reference data
    |
    v
[ DWD Layer ] -- cleaned facts, business keys, dimension joins
    |
    v
[ DWS Layer ] -- aggregated metrics at reporting grain
    |
    v
[ ADS Layer ] -- application-facing presentation tables
    |
    v
[ Dashboard / BI ]
```

---

## T-8: Table Schema Detail

> Use the 6-column format below for all schema sections (T-9 through T-14).

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|------------|---------------|-------------|-------------|
|             |           |            |               |             |             |

---

## T-9: ODS Table Columns

### ODS Contract Table

| Property              | Value                                          |
|-----------------------|------------------------------------------------|
| source                | _TODO: source system name_                     |
| grain                 | _TODO: one row per ..._                        |
| logical_partition     | _TODO: partition column (e.g., event_date)_    |
| incremental_strategy  | delete+insert                                  |
| unique_key            | _TODO: natural key column(s)_                  |
| backfill              | _TODO: initial load strategy_                  |
| restatement           | _TODO: how late-arriving data is handled_      |
| provenance_columns    | provider, pull_ts_utc, run_id                  |

### {prefix}_ods__ Columns

| column_name   | data_type   | definition                        | example_value       | calculation | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------|---------------|
| _TODO_        |             |                                   |                     | --          |               |
| provider      | VARCHAR     | Name of the data provider/source  | 'api_provider_name' | --          | system        |
| pull_ts_utc   | TIMESTAMP   | UTC timestamp of data extraction  | 2025-01-15 08:30:00 | --          | system        |
| run_id        | VARCHAR     | Unique identifier for the ETL run | 'run_20250115_0830' | --          | system        |

---

## T-10: DIM Table Columns

### dim_ Columns

| column_name   | data_type   | definition                        | example_value       | calculation | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------|---------------|
| _sk           | INTEGER     | Surrogate key                     | 1                   | row_number()| generated     |
| _TODO_        |             |                                   |                     |             |               |

---

## T-11: DWD Table Columns

### {prefix}_dwd__ Columns

| column_name   | data_type   | definition                        | example_value       | calculation | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------|---------------|
| _TODO_        |             |                                   |                     |             |               |

---

## T-12: Count DWS Table Columns

### {prefix}_dws_count_ Columns

| column_name   | data_type   | definition                        | example_value       | calculation       | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------------|---------------|
| _TODO_        |             |                                   |                     | COUNT(DISTINCT )  |               |

---

## T-13: Performance DWS Table Columns

### {prefix}_dws_perf_ Columns

| column_name   | data_type   | definition                        | example_value       | calculation       | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------------|---------------|
| _TODO_        |             |                                   |                     | SUM() / AVG()     |               |

---

## T-14: ADS / Presentation Table Columns

### {prefix}_ads__ Columns

| column_name   | data_type   | definition                        | example_value       | calculation | data_source   |
|---------------|-------------|-----------------------------------|---------------------|-------------|---------------|
| _TODO_        |             |                                   |                     |             |               |

---

## T-15: Physical Design

### Materialization Strategy

| Table                  | Materialization | Partition Key     | Cluster Key       |
|------------------------|-----------------|-------------------|-------------------|
| {prefix}_ods__         | incremental     |                   |                   |
| dim_                   | table           | --                | --                |
| {prefix}_dwd__         | table           | --                |                   |
| {prefix}_dws__         | table           | --                |                   |
| {prefix}_ads__         | table           | --                |                   |

### Storage Estimates

_TODO: Estimate row counts and storage per table for the initial load and steady-state daily increments._

---

## T-16: Coding

### Naming Conventions

- ODS: `{prefix}_ods_<source>_<entity>`
- DIM: `dim_<entity>`
- DWD: `{prefix}_dwd_<entity>_<grain>`
- DWS: `{prefix}_dws_<agg_type>_<entity>`
- ADS: `{prefix}_ads_<use_case>`

### dbt Project Structure

```
models/
  ods/
    {prefix}_ods__.sql
  dim/
    dim_.sql
  dwd/
    {prefix}_dwd__.sql
  dws/
    {prefix}_dws__.sql
  ads/
    {prefix}_ads__.sql
seeds/
  dim_date.csv
```

---

## T-17: Dashboard Specification

| Dashboard Panel | Chart Type     | Metrics Displayed      | Filter Dimensions        |
|-----------------|----------------|------------------------|--------------------------|
| _TODO_          | Line / Bar     |                        | date_range, entity       |

---

## T-18: DQC Plan

| Check Name           | Layer | Table                  | Rule                            | Threshold       |
|----------------------|-------|------------------------|---------------------------------|-----------------|
| freshness            | ODS   | {prefix}_ods__         | MAX(pull_ts_utc) < N hours ago  | 24 hours        |
| completeness         | DWD   | {prefix}_dwd__         | non-null ratio >= threshold     | 95%             |
| null_rate            | DWD   | {prefix}_dwd__         | null ratio <= threshold         | 5%              |
| volume_deviation     | ODS   | {prefix}_ods__         | row count within N% of prior    | 20%             |
| uniqueness           | ALL   | all tables             | unique_key has no duplicates    | 0 duplicates    |

---

## T-19: Test Case

| Test ID | Layer | Table                  | Test Type       | Description                                | Expected Result |
|---------|-------|------------------------|-----------------|--------------------------------------------|-----------------|
| TC-01   | ODS   | {prefix}_ods__         | unique          | Primary key uniqueness                     | 0 failures      |
| TC-02   | ODS   | {prefix}_ods__         | not_null        | Required columns are non-null              | 0 failures      |
| TC-03   | DWD   | {prefix}_dwd__         | relationships   | FK references resolve to dimension tables  | 0 failures      |
| TC-04   | DWS   | {prefix}_dws__         | accepted_values | Aggregation grain columns are valid        | 0 failures      |

---

## T-20: Job Monitoring and Alerts

| Job Name             | Schedule   | SLA          | Alert Channel | Escalation                    |
|----------------------|------------|--------------|---------------|-------------------------------|
| daily_pipeline       | cron TBD   | T+2 hours    | _TODO_        | Retry once, then notify owner |
| dqc_checks           | post-run   | T+30 min     | _TODO_        | Notify owner immediately      |

---

## T-21: Notable / Known Limitations

| ID   | Limitation Description                                      | Impact                | Mitigation              |
|------|-------------------------------------------------------------|-----------------------|-------------------------|
| L-1  | _TODO_                                                      |                       |                         |

> Carry forward any items from BRD section B-4 and add any new technical limitations discovered during design.
