# Methodology

mart-forge implements a generic, agent-executable version of the Kimball
data-warehouse lifecycle. The lifecycle is opinionated about *order* and
*gates*; it is intentionally agnostic about *domain* and *tools*.

This document is a reference. The enforcement of these rules lives in
`SPEC.md` and the skills under `.claude/skills/`.

## Phases at a glance

```
A0  source-discovery   -> docs/source_catalog.json
A   mart-brd            -> docs/business-requirements.md  (signed)
B   mart-tdd            -> docs/tech-design-doc.md        (signed)
C   mart-bootstrap      -> models/, seeds/, tests/, dashboard/
D   mart-dqc            -> dqc_scorecard.json
                            coverage_manifest.json
review  mart-review     -> readiness verdict
```

Each phase has a prerequisite artifact from the previous phase. Each
phase produces a deliverable that becomes the input to the next.

## Phase A0 — Source discovery

Discover, verify, and catalog data sources from stakeholder requirements
*before* writing the BRD.

For each metric:

1. **Provider enumeration.** List every plausible provider. No filtering yet.
2. **Five-point verification** per (metric, provider) pair:
   - Availability (does the provider respond?).
   - Asset identity (correct entity).
   - License/terms (usable under this repo's license).
   - Freshness/SLA (meets the mart's refresh cadence).
   - Semantic match (provider's field maps to the metric without lossy
     transformation).
3. **Resource exhaustion** before any metric is classified `unsupported`:
   enumerate alternatives, attempt each, document failures.
4. **Source catalog** (`docs/source_catalog.json`) writes the result with
   verification status per (metric, provider, check).

A metric without a non-empty source binding fails source-discovery
acceptance (SPEC §6.4) unless it is genuinely derived from other mart
layers.

## Phase A — Business Requirements Document (BRD)

The BRD is stakeholder-facing. Its job is to make the business intent
unambiguous so the technical design can be reviewed against intent, not
guessed.

Mandatory sections:

| § | Contents |
|---|----------|
| B-1 Version History | Draft -> signed, every revision tracked |
| B-2 Business Context | Process, purpose, stakeholder needs, glossary, verified data sources |
| B-3 Metrics Breakdown | Per-metric: name, source_type, link_status, public classification, verification evidence |
| B-4 Notable / Known Limitations | Unsupported metrics with exhaustion evidence, proxy warnings, freshness gaps |

The BRD is unsigned until the stakeholder and engineering owner both
sign the signature block at the bottom.

## Phase B — Technical Design Document (TDD)

The TDD is engineering-facing. It translates business intent into
precise column definitions, SQL, and ODS contracts.

Mandatory sections T-1 through T-21 (see SPEC §4.5 for the full list).
The bones:

- **T-4 Design Consideration** uses the 4-step Kimball method:
  business process -> grain -> dimensions -> facts.
- **T-5 Bus Matrix** maps facts to dimensions.
- **T-8 Schema Detail** uses a 6-column format per column:
  `column_name | data_type | definition | example_value | calculation | data_source`.
  The `calculation` column is the discipline lever: native columns read
  `pass-through from <provider.field>`; derived columns carry the
  literal SQL.
- **T-9 ODS Table Columns** carries the ODS contract: source, grain,
  logical partition, incremental strategy, unique key, backfill,
  restatement, provenance columns. Idempotence is required.
- **T-12** is *count* DWS; **T-13** is *performance* DWS. They are
  separate so that aggregations with different intent are easy to find
  and review.

## Phase C — Scaffold

`/mart-bootstrap` generates the dbt project from the signed TDD:

```
models/
├── ods/   pass-through ingestion with provenance columns
├── dim/   seed-backed conformed dimensions
├── dwd/   cleaned facts with business keys joined to dimensions
├── dws/   aggregations (count + performance)
└── ads/   application-facing one-big-tables
seeds/
tests/
dashboard/
```

The layer direction is one-way: ODS feeds DIM and DWD, DWD feeds DWS,
DWS feeds ADS. A `ref()` in the wrong direction is a CI failure caught
by `scripts/lint_layer_direction.py`.

## Phase D — Data Quality Contract (DQC)

The DQC catalog has 8 controls. Not every control applies to every
table; applicability is a function of layer and source type.

| # | Control | Severity | Applies to |
|---|---------|----------|-----------|
| 1 | PK Integrity | error | All tables |
| 2 | FK Integrity | error | Tables with FKs |
| 3 | Freshness | error | ODS/DWD |
| 4 | Completeness / Volume | warn | Tables with regular refresh |
| 5 | Accepted Ranges | warn | Numeric metrics |
| 6 | Duplicate Detection | error | Fact tables |
| 7 | Null-Rate Threshold | warn | All tables (threshold per column) |
| 8 | Business Reconciliation | error/warn | Only when an `exact` external comparator exists |

`dqc_scorecard.json` is generated mechanically from `dbt test` output.
The scorecard is the source of truth; the dashboard reads from it.

## Phase review — Readiness verdict

`/mart-review` produces a readiness grade by checking:

- Every BRD metric traces to a TDD column traces to a dbt model.
- Every column has the expected tests for its layer and source type.
- The dashboard displays the link-status badges correctly.
- The coverage manifest matches what is rendered.

A readiness grade of A is required to merge the final checkpoint.

## How to think about errors

Every linter and every gate produces an actionable error message. If
you find yourself reading an error and having to consult the spec to
understand what to do, file an issue against the linter — the error
message is the bug, not the rule it enforces.
