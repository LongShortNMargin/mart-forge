# Provider Abstraction

## Principle

mart-forge is methodology-first. The core value is at the transform and governance layer, not ingestion. Provider abstraction is intentionally thin in v1.

## Thin Ingestion Contract

Each ODS model defines a source contract:

```yaml
# In mart.yml
providers:
  primary: provider_name
  fallback: fallback_provider
  auth_required: false
```

The ODS model reads from the configured source and adds provenance columns. The contract specifies:
- Provider name and endpoint
- Authentication requirements
- Expected schema (explicit column list)
- Freshness SLA

## Source Selection Protocol

No provider is pre-selected. Source discovery (Phase A) verifies each candidate:

1. **Availability** — Does the endpoint respond?
2. **Identity** — Does the response contain the expected entity?
3. **License** — Is the data usable under Apache 2.0?
4. **Freshness** — Is data within acceptable SLA?
5. **Semantic match** — Does the field match the BRD metric?

Only after verification is a provider bound in the TDD.

## Adapter Pattern

The reference implementation uses dbt-duckdb. The ODS template reads from:
- CSV seeds (fixture/demo mode)
- httpfs/parquet (remote data via DuckDB)
- External tables (local files)

### Portability Contract

While v1 targets dbt-duckdb only, the methodology is warehouse-agnostic:
- Naming conventions apply to any warehouse
- Bus matrix, grain rules, DQC control catalog are portable
- Only `incremental_strategy` and source access patterns are adapter-specific

## Future Adapters

A portability contract for additional warehouses may be published separately. When adding a new adapter:
1. Implement ODS source reading for the target warehouse
2. Verify incremental strategy compatibility
3. Ensure DQC tests are portable
4. Document adapter-specific configuration in mart.yml
