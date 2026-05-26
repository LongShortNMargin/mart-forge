# Provider Abstraction — Data Provider Contract

## Overview

mart-forge treats data providers as pluggable components. A provider is any system
that delivers data into the ODS layer — whether it is a REST API, a flat file,
or a database connection. The provider abstraction ensures that the core pipeline
logic is decoupled from provider-specific details.

## Provider Types

| Type       | Description                                    | Example Sources              |
|------------|------------------------------------------------|------------------------------|
| `api`      | HTTP/REST endpoints polled on a schedule       | Market data APIs, weather services |
| `file`     | Flat files (CSV, JSON, Parquet) in a staging area | Exchange file drops, vendor exports |
| `database` | Direct connection to an external database      | Operational databases, replicas |

## Source Type Rules

Every column ingested through a provider is tagged with a `source_type` that
controls how it is treated in downstream layers:

| Source Type | Definition                                         | DQC Implications           |
|-------------|----------------------------------------------------|-----------------------------|
| `native`    | Pass-through from provider. Value is not altered.  | Freshness checks apply. Range checks use provider-defined bounds. |
| `derived`   | Computed via explicit SQL expression in mart.yml.  | No freshness check (depends on upstream freshness). Must document the SQL formula. |
| `hybrid`    | Table contains both native and derived columns.    | Freshness checked on native columns only. Each column's type declared individually. |

**Rule:** A column is `native` by default. To mark it `derived`, the mart.yml
entry must include the `expression` field with the SQL formula.

## Provider Registration in mart.yml

Providers are registered in the mart-level `mart.yml` configuration file. Each
provider entry defines the connection method, credentials reference, and SLA.

```yaml
# mart.yml — providers section
providers:
  yahoo_finance:
    type: api
    base_url: "https://query2.finance.yahoo.com"
    auth:
      method: env_var
      key: YAHOO_FINANCE_API_KEY
    freshness_sla:
      warn_after: {count: 2, period: hour}
      error_after: {count: 6, period: hour}
    rate_limit:
      requests_per_minute: 60
    source_type: native

  exchange_files:
    type: file
    staging_path: "data/staging/exchange/"
    file_pattern: "*.csv"
    auth:
      method: none
    freshness_sla:
      warn_after: {count: 1, period: day}
      error_after: {count: 3, period: day}
    source_type: native

  operational_db:
    type: database
    connection: "{{ env_var('OPS_DB_CONNECTION_STRING') }}"
    auth:
      method: env_var
      key: OPS_DB_CONNECTION_STRING
    freshness_sla:
      warn_after: {count: 1, period: hour}
      error_after: {count: 4, period: hour}
    source_type: native
```

## Authentication

**Credentials are NEVER committed to the repository.**

All provider authentication uses the `env_var` method:

1. The credential is stored as an environment variable on the execution host.
2. The `mart.yml` references the variable name, not the value.
3. dbt's `{{ env_var('...') }}` macro resolves it at runtime.

```yaml
auth:
  method: env_var
  key: PROVIDER_API_KEY    # name of the environment variable
```

For providers that require no authentication (e.g., public file drops), use:

```yaml
auth:
  method: none
```

**Supported auth patterns:**
- `env_var`: Single environment variable (API keys, connection strings).
- `none`: No authentication required.

Future auth methods (OAuth2, service accounts) will follow the same contract:
the mart.yml declares the method and key names; the runtime resolves them from
the environment.

## Freshness and SLA Requirements

Every provider must declare a freshness SLA — the maximum acceptable age of its
most recent data delivery. This feeds directly into DQC Control #3 (Freshness).

```yaml
freshness_sla:
  warn_after: {count: 2, period: hour}
  error_after: {count: 6, period: hour}
```

| Field         | Description                                          |
|---------------|------------------------------------------------------|
| `warn_after`  | Age threshold that triggers a DQC warning.           |
| `error_after` | Age threshold that halts the pipeline.               |
| `period`      | Time unit: `minute`, `hour`, `day`.                  |
| `count`       | Number of periods.                                   |

SLA is checked against `max(pull_ts_utc)` in the ODS table for that provider.

## How ODS Models Bind to Providers

Each ODS model declares which provider it sources from:

```yaml
# models/ods/mart.yml
models:
  - name: gme_ods_options_daily
    description: "Daily options chain data"
    meta:
      provider: yahoo_finance
      source_type: native
      grain: "one row per instrument per trading day"
    columns:
      - name: provider
        description: "Provider identifier"
      - name: pull_ts_utc
        description: "Extraction timestamp"
```

The `meta.provider` field links the model to the provider definition in the
top-level `mart.yml`. The `/mart-dqc` skill uses this link to apply the correct
freshness SLA.

## How to Add a New Provider

### Step 1: Define the Provider

Add an entry to the `providers` section of `mart.yml`:

```yaml
providers:
  new_vendor:
    type: api
    base_url: "https://api.newvendor.com/v1"
    auth:
      method: env_var
      key: NEW_VENDOR_API_KEY
    freshness_sla:
      warn_after: {count: 4, period: hour}
      error_after: {count: 12, period: hour}
    source_type: native
```

### Step 2: Set the Environment Variable

On every execution host (local dev, CI, production), export the credential:

```bash
export NEW_VENDOR_API_KEY="your-key-here"
```

### Step 3: Create the ODS Model

Create a new ODS model that ingests from the provider:

```sql
-- models/ods/gme_ods_new_data_daily.sql
{{ config(materialized='incremental', unique_key=['instrument_bk', 'trade_date']) }}

select
    'new_vendor'                as provider,
    current_timestamp()         as pull_ts_utc,
    ...
from {{ source('new_vendor', 'raw_data') }}
```

### Step 4: Bind the Model to the Provider

In the ODS layer's `mart.yml`, add the model entry with `meta.provider`:

```yaml
models:
  - name: gme_ods_new_data_daily
    meta:
      provider: new_vendor
      source_type: native
      grain: "one row per instrument per trading day"
```

### Step 5: Run DQC

Execute `/mart-dqc` to validate that the new provider's data meets all 8 controls.
The freshness check will use the SLA from the provider definition.

## Provider Lifecycle

| Stage        | Action                                              |
|--------------|-----------------------------------------------------|
| Discovery    | `/source-discovery` identifies available providers  |
| Registration | Developer adds provider to `mart.yml`               |
| Binding      | ODS models reference the provider via `meta.provider` |
| Validation   | `/mart-dqc` checks freshness, completeness, ranges  |
| Monitoring   | Scorecard tracks provider health across runs        |
| Retirement   | Remove provider entry and dependent ODS models      |

## Constraints

- One provider may feed multiple ODS models, but each ODS model binds to exactly
  one provider.
- Provider names must be unique within a mart.
- Provider names use `snake_case` and match the pattern `[a-z][a-z0-9_]*`.
- The `base_url` or `staging_path` is informational metadata — the actual
  extraction logic lives in the ODS model SQL or a pre-hook script.
