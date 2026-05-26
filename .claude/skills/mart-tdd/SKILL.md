---
name: mart-tdd
description: "Phase B -- produce a signed Technical Design Document (TDD) from the signed BRD, enforcing the hard gate before scaffold generation"
user-invocable: true
---

# mart-tdd -- Phase B: Technical Design Document

## When to use

Invoke this skill after the BRD has been signed and you need to produce the
technical design that will drive scaffold generation. The TDD translates business
requirements into precise column definitions, SQL calculations, and ODS contracts.

## Prerequisites

- `docs/business-requirements.md` exists with a **completed signature block**
  (both Stakeholder and Data Engineer rows filled).
- `mart.yml` has `brd_signed: true`.
- `docs/source_catalog.json` is available for source reference.

## Hard gate

```
GATE: No scaffold generation may begin until the TDD carries a valid signature block.
```

If the BRD is unsigned, reject the invocation immediately:

```
BLOCKED: BRD signature required before TDD authoring.
Run /mart-brd to complete Phase A.
```

## Workflow

### Step 1 -- Validate BRD signature

Read `docs/business-requirements.md`. Parse the signature table. Confirm both
rows have non-empty Name and Date fields. If validation fails, stop and report
which signatures are missing.

### Step 2 -- Load TDD template

Read `templates/tech-design-doc.md.tmpl`. The template defines sections T-1
through T-21:

| Section | Title | Content |
|---------|-------|---------|
| T-1 | Version History | Same format as B-1 |
| T-2 | Overview | Mart purpose, grain, refresh cadence |
| T-3 | Architecture | Layer diagram: ODS -> DIM -> DWD -> DWS -> ADS |
| T-4 | ODS Contracts | One table per source (see Step 3) |
| T-5 | DIM Layer | Dimension table definitions |
| T-6 | DWD Layer | Detail-grain fact definitions |
| T-7 | DWS Layer | Summary/aggregate definitions |
| T-8 | ADS Layer | Application-facing view definitions |
| T-9 | Column Catalog | Master 6-column table (see Step 4) |
| T-10 | Seed Data | Static reference data definitions |
| T-11 | Incremental Strategy | Per-model materialization and strategy |
| T-12 | Testing Plan | Test types mapped to DQC control classes |
| T-13 | Pipeline Orchestration | DAG description and scheduling |
| T-14 | Backfill Strategy | Historical data loading approach |
| T-15 | Restatement Protocol | How corrections propagate |
| T-16 | Performance | Partitioning, clustering, query patterns |
| T-17 | Security | Access controls, PII handling, masking |
| T-18 | Monitoring | Alerting thresholds and escalation |
| T-19 | Migration Plan | Rollout phases and rollback |
| T-20 | Open Questions | Unresolved items requiring stakeholder input |
| T-21 | Signature | Same format as BRD signature block |

### Step 3 -- Build ODS contract tables (T-4)

For each source in the source catalog, produce a contract table with these rows:

| Field | Description |
|-------|-------------|
| `source` | Provider and asset identifier |
| `grain` | Row-level granularity of the source |
| `partition` | Partition key(s) for incremental loads |
| `incremental_strategy` | append / merge / delete+insert / snapshot |
| `unique_key` | Natural key or composite key expression |
| `backfill` | Backfill window and strategy |
| `restatement` | How late-arriving or corrected data is handled |
| `provenance` | Lineage tag linking back to source catalog entry |

### Step 4 -- Build master column catalog (T-9)

For every column across all layers, produce a row in 6-column format:

| Column | Description |
|--------|-------------|
| `column_name` | Fully qualified: `<layer>.<model>.<column>` |
| `data_type` | SQL data type |
| `definition` | Business-English definition |
| `example_value` | Representative sample value |
| `calculation` | For derived columns: actual SQL expression. For native columns: `"pass-through from <provider>.<field>"` |
| `data_source` | Source catalog provider + asset reference |

**Constraint on `calculation` column**: Derived metrics must contain executable
SQL (not pseudocode or prose). Native metrics must use the exact format
`"pass-through from <provider>.<field>"`. Any other format is a review failure.

### Step 5 -- Fill remaining sections

Complete T-2 through T-20 using the BRD, source catalog, and standard mart-forge
conventions. Flag open questions in T-20 rather than making assumptions.

### Step 6 -- Write the TDD

Write `docs/tech-design-doc.md`. Append the signature block (T-21) in the same
format as the BRD.

### Step 7 -- Update mart.yml

Set `tdd_path` to `docs/tech-design-doc.md`. Set `tdd_signed` to `false`.
Set `phase` to `B_draft`.

### Step 8 -- Prompt for signature

Summarize the TDD for stakeholder review:

- Number of ODS contracts, models per layer, total columns.
- Any open questions from T-20 that block signing.

## Output format

Primary artifact: `docs/tech-design-doc.md`.
Secondary: updated `mart.yml`.

## NOT for

- Writing the BRD (use `/mart-brd`).
- Generating the dbt scaffold (use `/mart-bootstrap` after the TDD is signed).
- Running data quality checks (use `/mart-dqc`).
- Reviewing an existing TDD (use `/mart-review`).
