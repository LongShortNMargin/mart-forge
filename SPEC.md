# mart-forge — Governance and Conformance Contract (SPEC)

Status: APPROVED
Date: 2026-05-24
Confidentiality: PUBLIC — this document contains no proprietary content.

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` are to be interpreted as described in RFC 2119.

---

## 1. Problem Statement

Data warehouse frameworks face three structural challenges:

1. **Framework-product confusion.** Example implementations are treated as the product. The framework itself — the methodology, templates, skills, lifecycle gates, and agent harness — is never independently validated.
2. **Uncontrolled lineage.** Repositories accumulate dead branches, stale fixtures, and architectural shortcuts across iteration cycles. Patching in place leaves audit trails of rejected approaches.
3. **Missing governance.** No specification exists that (a) separates framework construction from conformance testing, (b) defines a structured trial protocol, (c) establishes sign-off authority, or (d) enforces reset-on-rejection semantics.

This specification defines the governance, lifecycle, and conformance contract for mart-forge — a framework-first build where conformance examples validate the framework, not the other way around.

---

## 2. Goals

- **Framework-first product identity:** mart-forge is a methodology-driven, agent-executable specification for scaffolding Kimball data warehouses. Examples are conformance exams, not the product.
- **Two-phase build contract:** Phase F (framework construction, zero example content) followed by Phase G (conformance trial using the framework).
- **Structured trial protocol:** Evidence-first design contracts (Shot 1) followed by implementation (Shot 2). Rejection triggers reset, not patching.
- **Source discovery as first-class requirement:** No provider is pre-selected. Every metric declares source type, link status, and verification path.
- **Confidentiality boundaries:** Framework artifacts contain zero private identifiers, paths, or operator-specific data.

---

## 3. Core Domain Model

### 3.1 Metric Contract

Every metric in a BRD/TDD declares classification and link status.

#### Source Type

| Type | Definition | Rule |
|------|-----------|------|
| `native` | Direct field from a data source | Pass-through ingestion; no computation in transform layer. Field mapping in TDD. |
| `derived` | Computed from native fields | Explicit SQL/formula in TDD `calculation` column. No placeholders. |
| `hybrid` | Combines native and derived components | Reconciliation rules required: which component is native, which derived, how they combine. |

#### Link Status

| Status | Definition | Rule |
|--------|-----------|------|
| `exact` | External source provides same metric with same methodology | DQC reconciliation test required. Tolerance defined. |
| `proxy` | Related but not identical external metric | Advisory plausibility check only. NOT ingestion provenance or DQC truth. |
| `unsupported` | No free external source after resource exhaustion | Requires `attempts[]` array documenting each resource tried. |
| `unverified` | Source exists but unchecked | Temporary. Must resolve before TDD sign-off. |

### 3.2 BRD (Business Requirements Document)

Stakeholder-facing document declaring what the mart measures and why.

**Mandatory sections:**

| # | Section | Requirements |
|---|---------|-------------|
| B-1 | Version History | Track revisions from draft through sign-off |
| B-2 | Business Context | Business purpose, domain context, why the mart exists |
| B-3 | Metrics Breakdown | Metrics catalog with `source_type` and `link_status` per metric; public/private classification |
| B-4 | Known Limitations | Constraints, unsupported metrics with resource exhaustion evidence, known gaps |

### 3.3 TDD (Technical Design Document)

Technical document with complete Kimball design.

**Mandatory sections:**

| # | Section | Requirements |
|---|---------|-------------|
| T-1 | Version History | Track revisions from draft through sign-off |
| T-2 | Design Reasoning | 4-step Kimball: business process → grain → dimensions → facts |
| T-3 | Table Summary | All table types (ODS, DIM, DWD, DWS, ADS) with purpose and grain |
| T-4 | Data Architecture Diagram | Layer-by-layer flow from source through all tiers |
| T-5 | Column Specification | Per table: `column_name \| data_type \| definition \| example_value \| calculation \| data_source` |
| T-6 | ODS Table Design | Source, grain, partition, incremental strategy, unique key, backfill, restatement, provenance |
| T-7 | Dimension Table Design | Conformed dimensions, seed-backed, SCD strategy |
| T-8 | Fact Table Design | Cleaned facts with business keys, source_type per metric |
| T-9 | Count Aggregation Design | Count-type DWS tables with explicit SQL per calculation |
| T-10 | Performance Aggregation Design | Ratio/performance DWS tables with explicit SQL |
| T-11 | Presentation Table Design | ADS/OBT tables with metric-to-column traceability |
| T-12 | Physical Design | Column-level spec for every table type |
| T-13 | Implementation Specification | dbt naming, materialization, ref() chain, Jinja patterns |
| T-14 | DQC Plan | Controls per applicability matrix with severity and source type |
| T-15 | Test Inventory | Test name, type, target model, expected result |
| T-16 | Operations | Refresh schedule, SLA, timezone, alerting, failure handling |
| T-17 | Known Limitations | Constraints, unsupported metrics, known data gaps |

---

## 4. Lifecycle

### 4.1 Program Phases

```
SPEC ──[approve]──► Phase F ──[framework complete]──► Phase G
                                                        │
                                                  Shot 1 ──[sign-off]──► Shot 2
                                                        │                    │
                                                 [reject] ──► reset     [reject] ──► regenerate
                                                                            │
                                                                      [accept] ──► promotion
```

### 4.2 Phase F — Framework Quality Iteration

**Objective:** Build and iteratively improve the framework on `main`. Example content MAY be present as conformance checkpoints; Phase F governs the ongoing quality loop for both the framework and its examples.

**Deliverables:**
- All templates (BRD, TDD, mart.yml, model SQL, seeds, tests, pipeline, dashboard)
- All agent skills with hard gates between lifecycle phases
- Plugin harness and session bootstrap hooks
- Documentation (methodology, naming conventions, agent orchestration, bus matrix, DQC framework)
- Public SPEC (this document)
- CI with framework-level tests

**Acceptance:**
- `main` contains a complete, self-contained framework
- Example content in `examples/` follows the lifecycle and declares coverage honestly (verified vs pending metrics with numerator/denominator)
- A data engineer can read the templates/docs and build a mart without seeing an example
- Plugin installs and session bootstrap fires correctly
- All skills have hard gates enforced
- Incomplete metric coverage is visible and recorded, not hidden behind a merge barrier

### 4.3 Phase G — Conformance Trial

**Gate:** Phase F framework deliverables MUST exist before Phase G trials begin. Phase F quality iteration continues in parallel with Phase G work.

#### Shot 1 — Source Discovery, BRD, and TDD

- Source discovery with verification per source selection checks
- BRD instance using the BRD template, with all comparison links verified
- TDD instance using the TDD template, with full Kimball design and column-level specs
- Grade A required on both BRD and TDD before proceeding

#### Shot 2 — Implementation

- Working mart reading from approved data sources
- DQC scorecard complete with all applicable controls
- Dashboard validated against signed dashboard specification
- CI green
- No proprietary content

**Rejection semantics:** Rejected output is never patched in place. A fresh branch is created for each attempt.

---

## 5. Source Discovery and Verification

### 5.1 Source Selection Principle

Source selection is NOT predetermined. For each metric, the executing agent MUST verify:

| Check | Question | Gate |
|-------|----------|------|
| Provider availability | Does the endpoint respond? Is data accessible? | Fail → try next provider |
| Correct identity | Does the response contain the expected asset/entity? | Fail → reject source |
| License usability | Is data usable under the repo's license? | Fail → document restriction |
| Freshness fitness | Is data within acceptable delay for the grain? | Fail → document SLA gap |
| Semantic match | Does the field semantically match the BRD metric? | Fail → cannot be `exact`. Record `proxy` if advisory-useful, else `rejected` |

### 5.2 Link Verification

Every claimed external comparison link MUST be verified before BRD/TDD sign-off:

| Field | Description |
|-------|------------|
| `url` | Exact URL tested |
| `capture_timestamp` | ISO-8601 timestamp of capture |
| `rendered_identity` | Asset/entity shown on the page |
| `rendered_metric` | Specific metric shown |
| `candidate_result` | `exact_match` / `advisory_proxy` / `rejected` |

### 5.3 Resource Exhaustion Protocol

Before any DQC control can be marked `unsupported`:
1. Enumerate all available resources
2. Attempt each with documented evidence (source, result, reason, date)
3. Only after ALL resources are attempted can `unsupported` status be assigned
4. The scorecard MUST include an `attempts[]` array for non-pass controls

---

## 6. Design Package Validation

The signed BRD/TDD package MUST be rejected if:

1. **Missing mandatory section.** Any section from the mandatory list absent from the package.
2. **Required table type omitted without rationale.** Each table type needs a column section or a signed `not_applicable` rationale.
3. **Metric without end-to-end traceability.** Every BRD metric must trace through source discovery → table design → physical design → dashboard specification.
4. **Table-summary-to-schema gap.** Every table in the summary must have a schema detail AND physical design entry.
5. **Unresolved metric classification.** Any `unverified` link_status at sign-off fails the gate.

---

## 7. DQC Contract

### 7.1 Control Catalog

| Control Class | Checks | Severity | Applicability |
|---------------|--------|----------|---------------|
| PK Integrity | PK not null, unique | `error` | All tables |
| FK Integrity | FK resolves to DIM row | `error` | Tables with foreign keys |
| Freshness | Data within SLA | `error` | ODS/DWD tables |
| Completeness | Row count within range | `warn` | Tables with regular refresh |
| Accepted Ranges | Numerics within bounds | `warn` | Numeric metrics |
| Duplicate Detection | No duplicate business keys | `error` | Fact tables |
| Null-Rate | Columns under null % | `warn` | All tables |
| Business Reconciliation | Metrics match external source | `error`/`warn` | When exact comparator exists |

### 7.2 Scorecard Linkage

The `dqc_scorecard.json` MUST be mechanically generated from `dbt test` results. Each entry includes `linked_dbt_tests[]` and `last_dbt_run` timestamp. Non-pass controls include `attempts[]`.

### 7.3 Link-Status Display Rules

| link_status | Dashboard Display |
|-------------|-------------------|
| `exact` | Verification link to external source |
| `proxy` | Advisory comparator, visibly distinguished, labelled "not ingestion provenance" |
| `unsupported` | "No external comparator available" with evidence reference |
| `unverified` | MUST NOT appear in accepted dashboard |

---

## 8. Quality Gates

| Gate | Description | Applies To |
|------|-------------|-----------|
| G-BRD | Grade A on BRD | Per trial (Shot 1) |
| G-TDD | Grade A on TDD | Per trial (Shot 1) |
| G-LINK | All comparison links verified with evidence | BRD/TDD (Shot 1) |
| G-FIXTURE | Fixture data labeled with manifest | TDD/implementation |
| G-ODS | ODS tables fully specified | TDD |
| G-CI | CI green | Implementation |
| G-CONFORM | DQC scorecard complete | Implementation |
| G-MERGE | PR against target branch | All phases |
| G-CONFIDENTIAL | No private content in public artifacts | All artifacts |
| G-HARNESS | Lifecycle flow exists with hard gates | Framework (Phase F) |

---

## 9. Failure and Recovery

### Shot 1 Rejection
- Classify as framework deficiency or domain misunderstanding
- Framework deficiency → revise framework, then new Shot 1
- Domain issue → revise BRD/TDD on fresh branch
- Never patch rejected output

### Shot 2 Rejection
- Classify as implementation or framework deficiency
- Implementation → regenerate from signed contract on fresh branch
- Framework → return to Phase F, void signed contract, new Shot 1 required
- Three failed Shot 2 attempts from same contract → escalation required

---

*SPEC approved. Framework-first: Phase F builds the framework with zero example content. Phase G validates the framework against a real domain. Rejection resets, never patches.*
