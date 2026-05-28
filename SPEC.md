# mart-forge — Program Specification

Status: First-commit baseline. The spec is treated as a living document —
version history lives in git, not in filename proliferation. There are no
versioned-spec or feedback-suffixed copies. If feedback changes the spec,
the spec is edited in place.

Purpose: Define the governance, lifecycle, and conformance contract for
mart-forge — a methodology-first, agent-executable specification for
scaffolding and reviewing Kimball data warehouses.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, RECOMMENDED,
MAY, and OPTIONAL are to be interpreted as described in RFC 2119.

The term **implementation-defined** signals intentional flexibility delegated
to the executing agent within a contract boundary set by this document.

---

## 1. Problem Statement

mart-forge is a long-running framework project that scaffolds Kimball data
warehouses through coordinated AI agents. It reads stakeholder requirements,
discovers data sources, produces signed design documents, and generates a
complete dbt-duckdb warehouse with tests, a DQC scorecard, and a presentation
dashboard.

The framework solves four operational problems:

- It turns Kimball methodology knowledge into an agent-executable lifecycle
  instead of tribal knowledge locked in a senior engineer's head.
- It separates the *framework product* (reusable methodology, templates,
  skills, and gates) from any specific *conformance example*, so
  domain-specific workarounds cannot contaminate the framework.
- It enforces hard gates between lifecycle phases — no scaffold without a
  signed Technical Design Document; no TDD without an approved Business
  Requirements Document — preventing the agent's natural bias toward
  jumping to implementation.
- It provides enough observability to operate and debug multi-agent
  warehouse construction: checkpoint PRs, coverage manifests, DQC
  scorecards, and classification ledgers.

The framework addresses three root failures from prior iterations:

1. **Framework-product confusion.** Prior iterations treated a specific
   warehouse as the product. The framework itself — the methodology,
   templates, skills, lifecycle gates — was never independently validated.
   Domain-specific fixes contaminated the framework; the framework was
   never proven to work on its own.

2. **Empty-main failure mode.** Prior iterations shielded all delivery
   behind prerequisite gates. The repository's `main` branch stayed empty
   while work accumulated in unmerged feature branches. A reviewer could
   not tell whether progress was 20% or 90%. Incremental checkpoint
   delivery — where each phase merges a reviewable artifact to `main` —
   eliminates this failure mode.

3. **Lack of dogfooding.** Prior conformance examples were hand-edited by
   implementation agents, not produced by invoking the framework's own
   skills. The framework's lifecycle was never exercised end-to-end on
   its own proof artifact. Conformance examples MUST be built by the
   framework, not alongside it.

Important boundary:

- mart-forge is a framework and orchestrator. It scaffolds warehouses
  and reviews them.
- Domain-specific business logic (trading signals, position sizing, risk
  management) is out of scope. The framework produces verified numbers;
  downstream consumers own interpretation.
- A conformance run delivers incrementally through checkpoint PRs.
  Intermediate checkpoints represent progress states, not success states.
  The conformance exam is complete only when all criteria in §15.3 are met.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Produce a **methodology-first, agent-executable DWH harness** that a data
  PM or data engineer can install and use to deploy a high-quality Kimball
  warehouse with dashboard.
- Deliver through **incremental checkpoint PRs** — each lifecycle phase
  (BRD, ODS, DIM, DWS, ADS, DQC, dashboard) merges independently to
  `main`. Defects at step N fix step N; prior accepted checkpoints are
  preserved.
- Enforce **source-native preference**: when a data provider exposes a
  metric directly, ingest it as a pass-through field. Compute derived
  metrics only when no provider offers the metric natively.
- Serve **two audiences**: (a) data engineers and data PMs who use the
  framework to scaffold their own warehouses; (b) downstream consumers
  who read the resulting dashboards and trust their labels.
- Enforce **dogfooding**: every conformance example MUST be built by
  invoking the framework's own skills in their documented order.
  Hand-edited artifacts that merely match the template shape do not
  satisfy conformance. Skill invocations MUST be traceable in
  `.skill-invocations.jsonl`.
- Maintain a **single living specification** (this document).

### 2.2 Non-Goals

- Real-time streaming data pipelines (batch/daily grain only).
- A hosted SaaS product or web UI beyond the dashboard template.
- Trading signals, financial advice, position sizing, or risk
  management logic.
- Operator-private analytics — out of scope for the public framework.
- Multi-tenant access or user authentication.
- Replacing dbt — this framework uses dbt as the transform engine,
  not as a competitor.
- Prescribing a specific cloud provider or data warehouse beyond the
  reference implementation (dbt-duckdb + MotherDuck).

---

## 3. System Overview

### 3.1 Product Architecture

```
mart-forge/
├── .claude/
│   ├── skills/                  # Methodology + lifecycle skills with hard gates
│   ├── settings.json            # Hooks and permission policy
│   └── worktree_init.sh         # Worktree primitive used by /pull and /push
├── .claude-plugin/
│   └── plugin.json              # One-command install manifest
├── templates/
│   ├── business-requirements.template.md
│   ├── tech-design-doc.template.md
│   ├── mart.yml.template
│   ├── models/                  # Per-layer SQL templates (ODS/DIM/DWD/DWS/ADS)
│   ├── seeds/                   # Seed CSV templates
│   ├── tests/                   # Test templates
│   ├── dashboard/               # Dashboard skeleton with dual-mode connection
│   └── pipeline/                # GitHub Actions workflow template
├── tests/
│   ├── test_*.py                # pytest suite with adversarial probes
│   └── skill-testing/           # Behavioral specs + static linter for skills
│       ├── catalog.yaml         # Registry of all skills with coverage tracking
│       ├── quality-rubric.md    # Category-specific pass/fail metrics
│       └── specs/               # Per-skill behavioral spec files
├── docs/
│   ├── METHODOLOGY.md           # Generic Kimball methodology
│   ├── naming-conventions.md
│   ├── bus-matrix.md
│   ├── dqc-framework.md
│   └── provider-abstraction.md
├── scripts/                     # Linters with teeth
│   ├── lint_brd.py
│   ├── lint_tdd.py
│   ├── lint_layer_direction.py
│   ├── validate_dogfood.py
│   ├── confidentiality_scan.py
│   └── lint_docs_freshness.py
├── SPEC.md                      # This specification
├── CLAUDE.md                    # Agent onboarding (≤120 lines, table of contents)
├── README.md                    # Public-facing landing page
├── pyproject.toml
└── LICENSE
```

### 3.2 Actors

The framework executes through a tiered agent model:

| Tier | Actor | Role | Authority |
|------|-------|------|-----------|
| 1 | Orchestrator | Owns this SPEC. Dispatches work, reviews gates, classifies ambiguous feedback, approves/rejects deliverables. Does NOT implement. | Full gate authority; operator-proxy when delegated |
| 2 | Adversarial Reviewer | Grades BRDs, TDDs, and conformance artifacts against this SPEC's quality rubric. Finds gate bypasses and structural defects. | Grade authority; infinite review iterations until grade A |
| 3 | Implementation Kin | Executes atomic tickets: writes code, templates, tests, docs. One active ticket at a time. Isolated worktrees. One-reviewable-change delivery. | Autonomous within ticket scope; cannot merge or bypass gates |

Agents are defined declaratively. Each skill in `.claude/skills/` declares
its allowed tools and the role under which it runs.

### 3.3 Repository Strategy

mart-forge lives in a **PUBLIC** repository. Any commit that contains
private document references, operator-specific data, or confidential
source identifiers is a **CRITICAL FAILURE** (§14).

### 3.4 Orchestration Isolation

Framework development and conformance testing SHOULD run in separate
orchestration projects to prevent cross-contamination. Conformance work
that lands in this repository MUST be authored from the public conformance
project — never imported from a private one.

### 3.5 External Dependencies

| Dependency | Required | Role |
|------------|----------|------|
| dbt-core + dbt-duckdb | Yes | Transform engine (reference implementation) |
| DuckDB (local) | Yes | Local development and CI warehouse engine |
| MotherDuck | Optional | Live dashboard warehouse target |
| Python 3.11+ | Yes | Scripts, ingestion adapters, dashboard, CLI |
| Streamlit (or equivalent) | Yes (dashboard) | Dashboard presentation layer |
| GitHub Actions | Yes | CI pipeline |
| Data provider(s) | Per-conformance | NOT pre-selected. Bound only by the signed TDD after source discovery. |

### 3.6 Collaboration Protocol

Every agent action follows the collaborative workflow:

```
1. Question    — Agent asks clarifying questions about the task
2. Options     — Agent presents 2-3 approaches with trade-offs
3. Decision    — Reviewer / orchestrator / human operator decides
4. Draft       — Agent produces the deliverable
5. Approval    — Reviewer asks: "May I write this to <filepath>?"
```

No file writes without explicit approval. No multi-file changes without
changeset approval. No commits without orchestrator instruction.

---

## 4. Core Domain Model

### 4.1 Framework Artifact

The primary deliverable. A complete, self-contained framework that can
scaffold a Kimball DWH from stakeholder input without any domain-specific
content.

Fields:
- `templates/` — BRD, TDD, mart.yml, model SQL per layer, seed CSV, test
  patterns, dashboard skeleton, CI pipeline.
- `.claude/skills/` — Methodology skills with hard gates plus lifecycle
  skills for commit, debug, land, pull, push, and issue tracking.
- `tests/` — pytest suite (linter unit tests, adversarial probes) plus
  the Skill Testing Framework (`tests/skill-testing/`).
- `docs/` — Methodology, naming conventions, bus matrix, DQC framework,
  provider abstraction, design docs, exec-plans, llms.txt references.
- `.claude-plugin/plugin.json` — One-command install manifest.
- `CLAUDE.md` — Agent onboarding (≤120 lines, table-of-contents pattern).
- `SPEC.md` — This specification.

### 4.2 Conformance Exam

A working mart built *using the framework* (not alongside it) that proves
the framework's methodology and tooling produce a trustworthy, verifiable
warehouse.

Fields:
- `examples/{exam-name}/` — The accepted conformance output. Only
  skill-produced trials land here.
- `mart.yml` — Configuration contract (generated after source discovery
  plus signed TDD, not before).
- `business-requirements.md` — Signed BRD instance (produced by
  `/mart-brd`).
- `tech-design-doc.md` — Signed TDD instance (produced by `/mart-tdd`).
- `models/` — dbt models (produced by `/mart-bootstrap`).
- `seeds/` — Static dimension and fixture data.
- `tests/` — DQC tests implementing the control catalog.
- `fixtures/` — Static test data with manifest.
- `dashboard/` — Dashboard with dual-mode connection.
- `dqc_scorecard.json` — Machine-readable quality artifact linked to
  `dbt test` results.
- `coverage_manifest.json` — `verified_count / planned_count` per metric.

### 4.3 Metric Contract

Every metric in a BRD/TDD declares two classifications.

#### 4.3.1 Source Type

| Type | Definition | Implementation Rule |
|------|-----------|---------------------|
| `native` | Metric exists as a direct field in a data source | Pass-through ingestion. No computation in the transform layer. TDD specifies field mapping only. `calculation` column reads "pass-through from `<provider.field>`". |
| `derived` | Metric is computed from native fields | Explicit SQL/formula in TDD `calculation` column. No "derived", "computed", or "see model" placeholders. |
| `hybrid` | Metric combines native and derived components | Reconciliation rules in TDD: which component is native, which is derived, how they combine, and what tolerance applies. |

#### 4.3.2 Link Status

| Status | Definition | Dashboard Display | DQC Rule |
|--------|-----------|-------------------|----------|
| `exact` | External source provides the same metric with the same methodology | Verification link icon labeled "Exact verification source" | Reconciliation test required with defined tolerance |
| `proxy` | External source provides a related but not identical metric | Advisory comparator link, visibly distinct, labeled "Advisory comparator — not DQC truth" | Cannot be used as DQC pass/fail truth |
| `unsupported` | No free external source exists after resource exhaustion (§6.3) | "No external comparator available" with evidence reference | Requires `attempts[]` documenting each resource tried |
| `unverified` | Source exists but has not been checked | MUST NOT appear in an accepted dashboard. Blocked at TDD sign-off. | Temporary only; must resolve before sign-off |

### 4.4 BRD (Business Requirements Document)

The first deliverable in a conformance exam. Stakeholder-facing. Produced
by `/mart-brd` against a source catalog.

Mandatory sections B-1 through B-4:

| # | Section | Purpose |
|---|---------|---------|
| B-1 | Version History | Track every revision from draft through sign-off |
| B-2 | Business Context | Business process, purpose, stakeholder needs, domain glossary, verified data sources (§6.1) |
| B-3 | Metrics Breakdown | Every metric with name, `source_type` (§4.3.1), `link_status` (§4.3.2), public classification, candidate verification evidence |
| B-4 | Notable / Known Limitations | Declared constraints, unsupported metrics with resource-exhaustion evidence (§6.3) |

### 4.5 TDD (Technical Design Document)

The second deliverable. Technical-facing. Produced by `/mart-tdd` after BRD
sign-off.

Mandatory sections T-1 through T-21:

| # | Section | Purpose |
|---|---------|---------|
| T-1 | Changelog | Track every revision from draft through sign-off |
| T-2 | Business Background | Domain context from BRD, tracing to stakeholder needs |
| T-3 | Metrics Breakdown | Traces every BRD metric to a table plus column plus source |
| T-4 | Design Consideration | 4-step Kimball method: business process -> grain -> dimensions -> facts |
| T-5 | Bus Matrix | Fact-to-dimension mapping |
| T-6 | Table Summary | Every table (ODS/DIM/DWD/DWS/ADS) with purpose and grain |
| T-7 | Data Architecture Diagram | Layer-by-layer flow |
| T-8 | Table Schema Detail | 6-column format per column: `column_name \| data_type \| definition \| example_value \| calculation \| data_source` |
| T-9 | ODS Table Columns | Per table: source, grain, logical partition, `incremental_strategy`, `unique_key`, backfill, restatement, provenance columns (§7.4) |
| T-10 | DIM Table Columns | Conformed dimensions; seed-backed where applicable |
| T-11 | DWD Table Columns | Cleaned facts with business keys |
| T-12 | Count DWS Table Columns | Count-type aggregations with explicit SQL |
| T-13 | Performance DWS Table Columns | Rate/average/percentile aggregations with explicit SQL |
| T-14 | ADS / Presentation Table Columns | Application-facing one-big-tables |
| T-15 | Physical Design | Coverage MUST span all tables in T-6 |
| T-16 | Coding | dbt model naming, materialization strategy, `ref()` chain, macro usage |
| T-17 | Dashboard Specification | Visualization list and link-status display rules per metric |
| T-18 | DQC Plan | Controls per §8.2 applicability matrix |
| T-19 | Test Case | Test inventory mapping every DQC control to an executable test |
| T-20 | Job Monitoring and Alerts | Refresh schedule, SLA, alerting channels, failure handling |
| T-21 | Notable / Known Limitations | Declared constraints carried from B-4 plus new technical limitations |

Count DWS and Performance DWS are separate sections (not merged). DQC Plan
and Test Case are separate (not merged). Job Monitoring and Notable are
separate (not merged). Any table type required by the design but absent
from the TDD requires a signed `not_applicable` rationale.

### 4.6 Checkpoint PR

An incremental, reviewable delivery unit. Each lifecycle phase produces
one checkpoint PR targeting `main`. Checkpoints are independent saved-states:
a defect at checkpoint N does NOT invalidate checkpoints 1 through N-1.

Fields: `phase`, `branch`, `artifacts`, `ci_status`, `review_status`,
`merge_status`.

### 4.7 Coverage Manifest

Machine-readable progress artifact tracking verified metric coverage.

Per-metric fields: `name`, `source_type`, `link_status`, `status`,
`last_verified_ts`, `last_failure_reason`, `evidence_uri`, `dqc_test_refs`.

Aggregates: `planned_count`, `verified_count`, `coverage_pct`.

### 4.8 Classification Ledger

A private artifact maintained in the orchestration repository. The public
`SPEC.md` carries only the schema definition.

Fields per entry: `timestamp`, `source`, `raw_feedback`, `classification`,
`ruling`, `override_trail`.

---

## 5. Lifecycle and State Machine

### 5.1 Program Phases

```
SPEC approved -> Phase F (framework on main) -> Phase G (conformance exam)
                                                       |
                                            +----------+-------------+
                                            | Checkpoint PR Loop     |
                                            |                        |
                                            | BRD + TDD -> ACCEPT    |
                                            |     |                  |
                                            | source-discovery + ODS |
                                            |     -> ACCEPT          |
                                            |     |                  |
                                            | DIM + DWD -> ACCEPT    |
                                            |     |                  |
                                            | DWS -> ACCEPT          |
                                            |     |                  |
                                            | ADS + dashboard ACCEPT |
                                            |     |                  |
                                            | DQC + scorecard ACCEPT |
                                            +------------------------+
```

### 5.2 Phase F — Framework Construction

**Objective:** Build the framework product on `main` with zero
domain-specific content.

**Deliverables:** All templates, all skills, plugin harness, Skill Testing
Framework, documentation, CI pipeline, SPEC.md.

**Acceptance:**
- `main` contains a complete, self-contained framework.
- Plugin installs and SessionStart hook fires.
- All skills have hard gates enforced.
- `pytest tests/` passes.
- `scripts/confidentiality_scan.py .` exits 0.
- A data engineer can read templates/docs and understand how to build a
  mart without any conformance example.

### 5.3 Phase G — Conformance Examination (Incremental Checkpoints)

**Objective:** Validate the framework against a real-world domain using
the framework's own skills.

**Gate:** Phase F MUST be complete and accepted before any Phase G work begins.

**G-DOGFOOD requirement:** Every conformance artifact MUST be produced by
invoking the framework's own skills in their documented order. Skill
invocations MUST be traceable in `.skill-invocations.jsonl`. Hand-edited
content that merely matches the template shape does not satisfy
conformance.

Checkpoints:

| # | Title | Process |
|---|-------|---------|
| 1 | BRD + TDD | `/source-discovery` -> `/mart-brd` -> reviewer grade A -> `/mart-tdd` -> reviewer grade A -> checkpoint PR |
| 2 | Source Discovery + ODS | Implement ODS ingestion per signed TDD T-9. Idempotence test (run twice, no double rows). |
| 3 | DIM + DWD | Implement dimension and fact models per T-10/T-11. FK integrity, grain discipline, business key uniqueness. |
| 4 | DWS | Implement DWS aggregations per T-12/T-13. Derived metrics match TDD SQL. |
| 5 | ADS + Dashboard | Implement ADS one-big-table per T-14. Build dashboard from T-17. Link-status display rules (§8.5). Coverage manifest as dashboard badge. |
| 6 | DQC + Scorecard | Implement DQC controls per §8.2. `dqc_scorecard.json` mechanically generated from `target/run_results.json`. |

### 5.4 Checkpoint Rollback Rules

| Defect Location | Action | Prior Checkpoints |
|----------------|--------|-------------------|
| Checkpoint N's own artifacts | Fix on a new branch from `main`, produce corrected checkpoint PR | KEPT (1..N-1 untouched) |
| Earlier checkpoint (BRD metric wrong, TDD column wrong) | Go back to THAT checkpoint, produce corrected PR | Later checkpoints may need reconciliation but are NOT auto-invalidated |
| Framework defect (template, skill, gate logic) | Return to Phase F. Fix framework on `main`. Delete affected conformance artifact. Rebuild via skill invocation (destruct-regenerate). | ALL conformance checkpoints re-evaluated against revised framework |

### 5.5 Phase F Harness-Quality Loop

Phase F runs CONTINUOUSLY alongside Phase G, never as a shield gate:

```
each Phase F iteration:
  1. Identify the harness defect (surfaced by Phase G checkpoint failure,
     adversarial review finding, or coverage regression).
  2. Fix the harness defect on main (template, skill, gate logic, scaffold,
     DQC pattern, dashboard component).
  3. Delete the affected conformance artifact from examples/.
  4. Invoke the framework's own skills to REBUILD the artifact (G-DOGFOOD).
  5. DQC check: every source maps to a metric; every metric maps back to
     BRD/TDD.
  6. If step 5 fails -> harness gap -> return to step 2.
  7. Coverage manifest: verified_count / planned_count MUST rise or a
     labelled defect MUST resolve.
```

**Three-strike escalation rule:** If any single checkpoint sees three
failed attempts (one initial plus two retries), escalate to the
orchestrator before any fourth attempt. The orchestrator MUST classify
the failure per §10.2 before authorizing further work.

---

## 6. Source Discovery and Metric Contract

### 6.1 Source Selection Principle

Source selection is NOT predetermined. For each metric candidate, the
executing agent MUST verify:

| Check | Question | Fail Action |
|-------|----------|-------------|
| Availability | Does the provider respond from the executing environment? | Try next provider |
| Asset Identity | Does the response contain the correct asset / entity? | Reject source — wrong-asset CANNOT be `exact` |
| License / Terms | Is the data usable under this repository's license? | Document restriction |
| Freshness / SLA | Is the data delayed within the mart's required cadence? | Document SLA gap |
| Semantic Match | Does the provider's field definition match the BRD metric definition? | Cannot be `exact`. Record `proxy` only if explicitly useful; otherwise `rejected`. |

### 6.2 Link Verification (G-LINK)

Every claimed external comparison link MUST be verified before BRD/TDD
sign-off. Verification MAY be browser-based or programmatic, but the
evidence record MUST capture: `url`, `capture_timestamp`,
`rendered_asset_identity`, `rendered_metric_identity`, `candidate_result`.

Classification rules:
- Wrong asset → `rejected`. Never `exact_match`, never `advisory_proxy`.
- Correct asset, different metric → `advisory_proxy` only if explicitly
  useful and clearly labelled; otherwise `rejected`.
- `exact_match` requires correct asset identity, correct metric identity,
  same methodology, and evidence confirming all three.

Resolving metric-level `link_status` from candidate results:
- Any `exact_match` → metric `link_status` = `exact`.
- No `exact_match` but at least one `advisory_proxy` → `proxy`.
- All `rejected` plus §6.3 resource-exhaustion complete → `unsupported`.
- Untested candidates remain → `unverified` (blocked at sign-off).

### 6.3 Resource Exhaustion Protocol

Before any DQC control can be marked `unsupported`, the agent MUST:

1. Enumerate all available resources from the BRD plus candidate source
   inventory plus stakeholder input.
2. Attempt each resource and document: source name, result
   (`pass` / `blocked` / `error`), reason, date, evidence URI, provider
   version, reproducible command.
3. Only after ALL resources are attempted with documented evidence can
   `unsupported` status be assigned.
4. `dqc_scorecard.json` MUST include an `attempts[]` array for every
   non-`pass` control.

### 6.4 Source-Discovery Acceptance Criteria

All non-DWS metrics MUST NOT be empty or unavailable as a result of
`/source-discovery`. If a provider exists for a metric, that metric MUST
have a non-empty source binding in the BRD. A metric marked `unsupported`
MUST have §6.3 exhaustion evidence, not a bare waiver.

---

## 7. BRD/TDD Design Contract

### 7.1 Structural Standard

The BRD and TDD templates encode an industry-standard warehouse
design-document layout. The `calculation` column on every schema-detail
row MUST contain:

- For native columns: `pass-through from <provider.field>`.
- For derived columns: actual SQL or formula. No "derived", "computed",
  "see model" placeholders.
- For hybrid columns: both the native component reference and the
  derivation formula, with reconciliation tolerance.

### 7.2 BRD Template Requirements

`templates/business-requirements.template.md` MUST include all sections
B-1 through B-4 (§4.4). Additional validation:

| Aspect | Validation |
|--------|-----------|
| Every metric in B-3 | Has `source_type`, `link_status`, public classification |
| Every data source in B-2 | Has verification results from §6.1 checks |
| B-4 (Notable) | Every `unsupported` metric has §6.3 exhaustion evidence |
| Source-discovery acceptance | All non-DWS metrics MUST NOT be empty (§6.4) |

### 7.3 TDD Template Requirements

`templates/tech-design-doc.template.md` MUST include all sections T-1
through T-21 (§4.5). Additional validation:

| Aspect | Validation |
|--------|-----------|
| T-4 (Design Consideration) | All 4 Kimball steps present and non-empty |
| T-5 (Bus Matrix) | >=1 fact and >=1 dimension mapped |
| T-8 (Schema Detail) | Every column has all 6 fields; `calculation` has actual SQL for derived |
| T-9 (ODS) | Every ODS table has all 8 contract fields (§7.4). Idempotence verification required. |
| T-6 (Table Summary) | Every entry traces forward to T-8 Schema Detail AND T-15 Physical Design |
| T-15 (Physical Design) | Coverage spans ALL table types in T-6 |
| T-18 (DQC Plan) | Controls per §8.2 applicability matrix; non-applicable controls documented with rationale |

### 7.4 ODS Table Contract

Every ODS table in a daily-grain mart MUST define:

| Field | Description |
|-------|------------|
| `source` | Provider + endpoint/method |
| `grain` | One row represents... |
| `logical_partition` | Column for incremental windowing |
| `incremental_strategy` | Valid dbt-duckdb strategy |
| `unique_key` | Deduplication composite |
| `backfill` | How to load historical data |
| `restatement` | Behavior when source data is corrected |
| `provenance_columns` | Audit trail fields (provider, pull_ts_utc, run_id) |

Idempotence: running the same partition value twice MUST produce
identical output. CI MUST include a rerun idempotence test.

### 7.5 Grade Gates

Two mandatory grade gates per conformance exam:

- **G-BRD:** Adversarial reviewer grades the BRD. Grade A required. No
  TDD until BRD reaches grade A.
- **G-TDD:** Adversarial reviewer grades the TDD. Grade A required. No
  scaffold until TDD reaches grade A.

Neither gate may be skipped. Adversarial review has no iteration budget
cap.

### 7.6 Design Package Validation

The signed BRD/TDD package MUST be rejected if any of:

1. **Missing mandatory section.** Any §4.4 or §4.5 section absent.
2. **Table type omitted without rationale.**
3. **Metric without end-to-end traceability** through source discovery,
   TDD table column, TDD physical design, and signed dashboard spec.
4. **Table-summary-to-schema-detail gap.**
5. **Unresolved `link_status`.** Any `unverified` at TDD sign-off.

---

## 8. Scaffold / DQC / Dashboard Contract

### 8.1 Scaffold Output

Phase C (scaffold from signed TDD) MUST produce the standard directory
structure:

```
examples/{exam-name}/
├── mart.yml
├── business-requirements.md     (signed)
├── tech-design-doc.md           (signed)
├── models/
│   ├── ods/
│   ├── dim/
│   ├── dwd/
│   ├── dws/
│   └── ads/
├── seeds/
├── tests/
├── fixtures/
├── dashboard/
├── dqc_scorecard.json
├── coverage_manifest.json
├── dbt_project.yml
├── profiles.yml
└── .github/workflows/daily.yml
```

### 8.2 DQC Control Catalog

Eight control classes. Applicability is scoped per table, metric, and
source type — not every control applies to every table.

| # | Control Class | Checks | Severity | Applicability |
|---|---------------|--------|----------|---------------|
| 1 | PK Integrity | PK not null + unique | `error` | All tables |
| 2 | FK Integrity | FK resolves to DIM row | `error` | Tables with foreign keys |
| 3 | Freshness | Most recent `pull_ts_utc` within SLA | `error` | ODS/DWD |
| 4 | Completeness / Volume | Row count within expected range vs prior run | `warn` | Tables with regular refresh |
| 5 | Accepted Ranges | Numeric metrics within plausible bounds | `warn` | Native + derived numeric metrics |
| 6 | Duplicate Detection | No duplicate business keys within grain window | `error` | All fact tables |
| 7 | Null-Rate Threshold | Non-PK columns under configured null percentage | `warn` | All tables |
| 8 | Business Reconciliation | Key metrics match external source within tolerance | `error`/`warn` | Only when an `exact` external comparator exists |

Applicability by source type:
- `native`: PK integrity, provenance, freshness, pass-through field checks.
- `derived`: PK integrity, formula tests, accepted ranges. Explicit SQL
  validation.
- `hybrid`: PK integrity, provenance, formula tests, documented
  reconciliation.

Controls not applicable to a table/metric carry a `not_applicable` entry
with rationale in the scorecard.

### 8.3 Scorecard Linkage

`dqc_scorecard.json` MUST be mechanically generated from
`target/run_results.json` after `dbt test`. The scorecard MUST NOT be
stale versus actual test outcomes. Non-pass statuses are NEVER displayed
as green/pass.

### 8.4 Fixture and Live Mode Separation

| Mode | Data Source | Display Rule |
|------|-----------|-------------|
| Fixture / demo | Static parquet or CSV with manifest | Dashboard MUST show explicit "FIXTURE/DEMO" banner. Never claim fixture is live. |
| Live / operator | Warehouse populated from approved sources | Dashboard pulls from warehouse. Displays "BLOCKED/STALE" if data unavailable — never substitutes fixture silently. |

The fixture manifest MUST include source date, source URL/provider,
captured value, row count, and schema hash.

### 8.5 Dashboard Contract

The dashboard MUST:
- Include useful visualizations from the signed TDD dashboard spec — not
  metric-cards-only.
- Consume DQC results and provenance — never ask users to key reference
  values manually.
- Display external comparison links per `link_status`:
  - `exact` → verification link labeled "Exact verification source".
  - `proxy` → visibly distinct advisory comparator labeled "Advisory
    comparator — not ingestion provenance".
  - `unsupported` → "No external comparator available" with evidence
    reference.
  - `unverified` → MUST NOT appear (blocked at TDD sign-off).
- Distinguish fixture mode from live mode visually.
- Render coverage manifest as a dashboard badge:
  `Data Loaded N/M | DQC Verified N/M`.
- Trace every metric to a TDD entry.

Warehouse credentials are environment-sourced and NEVER committed.

---

## 9. Quality Gates

Every gate MUST pass before its gated phase can proceed. Gates are checked
by the adversarial reviewer or CI; the orchestrator records the verdict.

| Gate | Description | Applies To | Enforcement |
|------|-------------|-----------|-------------|
| G-SPEC | This specification reviewed and approved | Program level | Blocks all repo work until approved |
| G-BRD | Adversarial reviewer grade A on BRD | Per conformance exam | No TDD without grade A |
| G-TDD | Adversarial reviewer grade A on TDD | Per conformance exam | No scaffold without grade A |
| G-LINK | All candidate comparison links verified per §6.2 | BRD/TDD | Unverified metrics blocked at sign-off |
| G-FIXTURE | Fixture data labeled with manifest; no fixture presented as live | Implementation | CI check + dashboard banner enforcement |
| G-ODS | Every ODS table satisfies §7.4. Idempotence test green. | TDD + Implementation | Checkpoint 2 acceptance |
| G-DOGFOOD | Conformance example built by invoking framework's own skills. Invocations recorded in `.skill-invocations.jsonl`. | Phase G (all checkpoints) | CI enforcement via `scripts/validate_dogfood.py` |
| G-HONEST-LABEL | No metric on dashboard shows a value without its status badge. | Dashboard | CI check + rendering validation |
| G-ITERATIVE | Each Phase F iteration measurably raises coverage or resolves a labelled defect | Phase F loop | Orchestrator enforcement |
| G-CI | GitHub Actions green on `main` after each checkpoint merge | All checkpoints | Branch protection |
| G-MERGE | Every PR: reviewer non-blocking AND CI green | All phases | Branch protection + review requirement |
| G-CONFIDENTIAL | Zero operator-position data, zero private paths, zero internal project names in public commits | ALL commits | `scripts/confidentiality_scan.py` |
| G-CORRECT | Inaccurate values are NEVER acceptable. Coverage growth from relaxed verification = CI-blocking defect. | All phases | Adversarial review probe |

---

## 10. Failure and Recovery

### 10.1 Checkpoint-Level Rollback

See §5.4.

### 10.2 Three-Strike Escalation

One initial attempt plus two failed retries (three total) on ANY
checkpoint triggers escalation to the orchestrator before any fourth
attempt. The orchestrator MUST classify the failure as:

- **Framework viability issue** — the framework cannot produce a correct
  result from this contract. Requires contract revision.
- **Implementation variance** — the framework works but the kin's
  execution is incorrect. Requires different kin or more specific
  instructions.
- **Source availability issue** — the framework and kin are correct but
  data providers are unreachable. Requires environment remediation.

### 10.3 Human Operator Override

The human operator MAY override any ruling at any time:
- Override of a rejection → work continues from current state.
- Override of an approval → work product is voided; reset to appropriate phase.
- All overrides recorded in the Classification Ledger override trail.

---

## 11. Coordination and Workspace Safety

### 11.1 Concurrency Rule

One active implementation ticket at a time per agent. The implementation
kin does not run concurrent tickets. The adversarial reviewer MAY run
concurrent grading tasks, but only one implementation worktree is
active.

### 11.2 Worktree Isolation

- All implementation work happens in isolated worktrees, never in a
  shared checkout.
- Worktree paths SHOULD follow `/tmp/mart-forge-<ticket-slug>/` or an
  equivalent agent-runtime convention.
- If a worktree branch or path already exists or is dirty, the agent
  MUST report the conflict and choose a new path. Never reset or delete
  existing work.

### 11.3 Orchestration Dispatch

All implementation and artifact-writing work MUST be dispatched through
the orchestration platform. Read-only consultation remains permitted
outside dispatch for gate sign-off, rejection classification, and
clarification.

### 11.4 Collaboration Protocol

Every agent follows the 5-step workflow (§3.6). Agents MUST ask before
writing files. Multi-file changes require explicit changeset approval.

---

## 12. Skill Testing Framework

### 12.1 Structure

```
tests/skill-testing/
├── catalog.yaml           Registry: all skills with coverage tracking
├── quality-rubric.md      Category-specific pass/fail metrics
└── specs/
    ├── source-discovery.spec.md
    ├── mart-brd.spec.md
    ├── mart-tdd.spec.md
    ├── mart-bootstrap.spec.md
    └── mart-dqc.spec.md
```

### 12.2 Behavioral Spec Format

Each skill spec includes:

| Section | Content |
|---------|---------|
| Summary | One paragraph: what the skill does, when to use it |
| Domain | Files/directories the skill owns |
| Static Assertions | Structural checks (frontmatter fields, section headers, required gates) |
| Test Cases | 3-5 cases: happy path, rejection path, edge case, out-of-domain redirect |
| Case Verdict | PASS / FAIL / PARTIAL per case |

### 12.3 Enforcement

- `pytest tests/` runs all unit tests for linters and the static structural
  checks against every spec file.
- The static checks MUST pass in CI.
- The `mart-bootstrap` behavioral spec asserts that a fixture BRD/TDD
  produces expected scaffold output.

### 12.4 Adversarial Probe Cases

Every signed-contract gate MUST have adversarial probe cases:

- **Grade bypass:** Remove `Grade: A` from both docs; `APPROVED` alone
  should NOT pass.
- **Empty binding bypass:** Remove all metric-to-column mappings; scaffold
  should REJECT.
- **Bogus classification:** Set `link_status: bogus`; validator should
  REJECT.
- **Contract / output mismatch:** Sign a contract for metric X; scaffold
  should produce metric X, not a hard-coded default.

---

## 13. Observability

### 13.1 Coverage Manifest

The `coverage_manifest.json` is the program's primary progress metric.
Mechanically generated. Rendered as a dashboard badge. Updated on every
checkpoint merge.

### 13.2 Checkpoint Traceability

Each checkpoint PR MUST include commit SHA, artifact list, gate verdicts
with timestamps, reviewer grade with findings summary, and a link to the
orchestration issue.

### 13.3 Classification Ledger

The Classification Ledger (§4.8) records every ruling on ambiguous
feedback. The ledger content is private — it lives ONLY in the
orchestration repository. The public `SPEC.md` includes the SCHEMA but
NOT populated entries.

### 13.4 Program Ledger

A human-readable status surface maintained alongside this SPEC. Updated
when a gate state changes, a phase state changes, a checkpoint merges or
is rejected, or a blocker is recorded or resolved.

---

## 14. Trust and Confidentiality

### 14.1 Confidentiality Boundary

This is a PUBLIC repository. The following rules are non-negotiable.

MUST NOT appear in any commit, any branch, any file (see
`scripts/confidentiality_scan.py` for the literal patterns enforced):
- Operator-specific trading or business data — quantitative holdings,
  acquisition references, account identifiers, tactical rules, risk
  protocol parameters.
- Private file paths: cloud-drive paths, local user paths, private
  repository paths.
- Internal project identifiers: names of private projects, internal
  agent persona names, internal repository names.
- Confidential methodology names: proprietary reference documents,
  proprietary company names.
- Competitor framing: positioning against named competitors.

**Any violation is a CRITICAL FAILURE.** The commit MUST be reverted.
CI confidentiality scan MUST reject the commit before it reaches `main`.

### 14.2 CI Confidentiality Scan

`scripts/confidentiality_scan.py` runs on every PR. It fails the build if
any banned string is detected and reports file, line, and matched
pattern. Cannot be bypassed by any agent.

### 14.3 Trust Posture

| Action | Gate |
|--------|------|
| Code changes in worktrees | Autonomous (within ticket scope) |
| Orchestration ticket management | Autonomous |
| CI-only operations | Autonomous |
| Merge to `main` | Reviewer approval + CI green (branch protection) |
| Checkpoint sign-off | Reviewer grade A + orchestrator approval |
| Credential handling | Environment-sourced only; NEVER committed |
| Destructive operations (force-push, branch delete, DB drop) | Human operator approval |
| Public-facing content review | Orchestrator approval + confidentiality scan |

---

## 15. Validation Matrix

### 15.1 Phase F Acceptance

- [ ] `main` contains complete framework (templates, skills, docs, plugin,
  hooks, CLAUDE.md, SPEC.md).
- [ ] Zero domain-specific content on `main`.
- [ ] Plugin manifest valid.
- [ ] All skills have hard gates enforced.
- [ ] `pytest tests/` passes.
- [ ] CI green including confidentiality scan.
- [ ] A data engineer can understand how to build a mart from
  templates/docs alone.

### 15.2 Per-Checkpoint Acceptance

| Checkpoint | Acceptance Criteria |
|-----------|---------------------|
| 1 (BRD+TDD) | BRD grade A, TDD grade A, all non-DWS metrics bound (§6.4), all links verified, `coverage_manifest.json` generated |
| 2 (ODS) | ODS models match T-9, incremental strategy works, idempotence test passes, provenance columns present |
| 3 (DIM+DWD) | FK integrity, grain discipline, business key uniqueness, columns match T-10/T-11 |
| 4 (DWS) | Derived metrics match TDD SQL, window functions correct, aggregations produce expected shapes |
| 5 (ADS+Dashboard) | Dashboard renders from signed spec, link-status display correct, coverage badge renders, dual-mode connection works |
| 6 (DQC+Scorecard) | Applicable controls pass, non-applicable documented, scorecard mechanically linked to dbt results, `attempts[]` present for non-pass |

### 15.3 Conformance Exam Complete

- [ ] All 6 checkpoints merged to `main`.
- [ ] All quality gates (§9) pass.
- [ ] G-DOGFOOD verified: every artifact built by skill invocation with
  traceable evidence.
- [ ] Coverage manifest shows verified_count > 0 with honest per-metric
  statuses.
- [ ] Dashboard renders live on designated port.
- [ ] Confidentiality scan passes across all committed files.
- [ ] Adversarial reviewer has no outstanding blocking findings.

---

## 16. Session State and Agent Memory

### 16.1 Live Orchestrator State

If a session-state file exists, the orchestrator updates it every session
and auto-loads it at session start. The canonical path is
`production/session-state/active.md` (created when first needed; not
required for the framework itself).

### 16.2 Per-Agent Persistent Memory

`.claude/agent-memory/<agent>/MEMORY.md` accumulates per-agent learnings
across sessions: canonical paths (verified, not assumed), completed
skills and outcomes, learned conventions.

### 16.3 Boot Hook Integration

If a SessionStart hook is present, it emits directives to:
1. Read `production/session-state/active.md` before any user task.
2. Read the agent's own MEMORY.md if it exists.
3. Check the SPEC.md version line to confirm the active governance
   contract.

---

## Appendix A: Classification Ledger (schema only)

The public `SPEC.md` carries Appendix A as the empty schema below — never
with populated entries.

| Timestamp | Source | Raw Feedback | Classification | Ruling | Override Trail |
|-----------|--------|-------------|---------------|--------|---------------|
| — | — | — | — | — | — |

---

## Appendix B: Program Ledger (schema only)

Snapshot of phase status. Updated by the orchestrator.

| Phase | Status | Latest Evidence | Blockers |
|-------|--------|----------------|----------|
| G-SPEC | — | — | — |
| Phase F | — | — | — |
| Phase G | — | — | — |
