# Provider Abstraction

Data providers are the upstream edge of the warehouse. mart-forge does
not pre-select providers; it declares the *contract* a provider must
meet, leaving the binding to the signed TDD.

## What a provider is

A provider is anything that supplies raw data to the ODS layer. Common
examples: a REST API, a CSV drop, a SaaS event stream, an upstream
database. A provider is identified by:

- A short slug (`cboe`, `yfinance`, `s3_orders_drop`).
- An endpoint or path (`/api/v1/options-chain`, `s3://bucket/prefix/`).
- A field mapping that connects provider fields to ODS columns.

## The provider contract

Every provider used by a mart MUST satisfy:

| Requirement | Why |
|-------------|-----|
| **Deterministic identity** | The same pull on the same date yields the same response (modulo provider-side restatements). |
| **Asset identifiability** | The response says, programmatically, which entity it concerns. |
| **License compatibility** | Redistribution rules are compatible with the repository's license. |
| **Freshness SLA** | Update cadence is at least as fast as the mart's grain. |
| **Semantic match** | The provider's fields map to the BRD metric definitions without lossy transformation. |

If any of these fail, the provider is `rejected` for the relevant metric
and the resource-exhaustion protocol (SPEC §6.3) records the attempt.

## Ingestion adapters

The framework does not ship ingestion adapters. Each mart writes its own
under `scripts/` (or a per-mart `ingest/`) and registers them in
`mart.yml`. An adapter:

- Has a single entry point.
- Is invoked with `--pull-date <date>` for incremental loads.
- Writes its output to a parquet/CSV under `fixtures/` (for tests) or to
  the warehouse directly (for live mode).
- Logs `provider`, `pull_ts_utc`, `quote_ts_utc`, and `run_id` to the
  output as provenance columns.

A typical adapter:

```python
def pull(pull_date: str, output_path: str) -> None:
    """Pull one day of <provider> data and write to <output_path>.

    Provenance columns (provider, pull_ts_utc, quote_ts_utc, run_id) are
    appended to every row.
    """
    ...
```

## The ODS contract

Every ODS table declares the provider binding in §T-9 of the TDD:

```yaml
source: cboe.options-chain via yfinance v0.2.31
grain: one option contract on one pull date
logical_partition: pull_date
incremental_strategy: delete+insert
unique_key: ['pull_date', 'option_symbol']
backfill: dbt run --vars '{pull_date: "2026-05-01"}'
restatement: re-run for the affected pull_date; delete+insert replaces
provenance_columns: provider, pull_ts_utc, quote_ts_utc, run_id
```

The contract is enforced by `scripts/lint_tdd.py`. Missing fields fail
the lint.

## Swapping providers

A provider swap is a checkpoint-level change. The procedure:

1. Update the BRD §B-2 data-source row with the new provider and the
   verification result.
2. Update the TDD §T-9 ODS contract with the new `source`, mapping,
   incremental strategy, and any restatement difference.
3. Regenerate the ODS model via `/mart-bootstrap` (or `/schema-evolve`
   for additive-only changes).
4. Re-run the idempotence test.

A provider swap that changes the metric definition is NOT additive — it
is a re-write of the BRD and TDD, not a propagation.

## Why not a runtime provider abstraction?

mart-forge does not provide a runtime layer that wraps providers. The
reason is in `DESIGN.md` §2 (boring tech): wrapping providers at runtime
creates a second mental model on top of dbt. The seam is in the *spec*
— the ODS contract — not in code.

## Referenced from

- `SPEC.md` §7.4 (ODS Table Contract).
- `templates/tech-design-doc.template.md` §T-9.
- `scripts/lint_tdd.py` (validates the contract fields).
