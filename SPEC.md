# mart-forge — Program Specification

Status: APPROVED [ARGENT-PROXY 2026-05-27T00:50:00Z] (iteration 3, grade A after 6 adversarial review passes)
Date: 2026-05-27
Purpose: Define the governance, lifecycle, and conformance contract for mart-forge v3 — a methodology-first, agent-executable specification for scaffolding and reviewing Kimball data warehouses.

The key words `MUST`, `MUST NOT`, `REQUIRED`, `SHOULD`, `SHOULD NOT`, `RECOMMENDED`, `MAY`, and `OPTIONAL` are to be interpreted as described in RFC 2119.

The term **implementation-defined** signals intentional flexibility delegated to the executing agent within a contract boundary set by this document.

---

## 1. Problem Statement

mart-forge is a long-running framework project that scaffolds Kimball data warehouses through coordinated AI agents. It reads stakeholder requirements, discovers data sources, produces signed design documents, and generates a complete dbt-duckdb warehouse with tests, a DQC scorecard, and a presentation dashboard.

The framework solves four operational problems:

- It turns Kimball methodology knowledge into an agent-executable lifecycle instead of tribal knowledge locked in a senior engineer's head.
- It separates the *framework product* (reusable methodology, templates, skills, and gates) from any specific *conformance example* (e.g., a GME options mart), so domain-specific workarounds cannot contaminate the framework.
- It enforces hard gates between lifecycle phases — no scaffold without a signed Technical Design Document; no TDD without an approved Business Requirements Document — preventing the agent's natural bias toward jumping to implementation.
- It provides enough observability to operate and debug multi-agent warehouse construction: checkpoint PRs, coverage manifests, DQC scorecards, and classification ledgers.

The framework addresses three root failures from prior iterations:

1. **Framework-product confusion.** Prior iterations treated the GME options mart as the product. The framework itself — the methodology, templates, skills, lifecycle gates — was never independently validated. GME-specific fixes contaminated the framework; the framework was never proven to work on its own.

2. **Empty-main failure mode.** Prior iterations shielded all delivery behind prerequisite gates. The repository's `main` branch stayed empty while work accumulated in unmerged feature branches. The operator could not tell whether progress was 20% or 90%. Incremental checkpoint delivery — where each phase merges a reviewable artifact to `main` — eliminates this failure mode.

3. **Lack of dogfooding.** The canonical GME conformance example was hand-edited by implementation agents, not produced by invoking the framework's own skills (`/source-discovery`, `/mart-brd`, `/mart-tdd`, `/mart-bootstrap`). The framework's lifecycle was never exercised end-to-end on its own proof artifact. Conformance examples MUST be built by the framework, not alongside it.

Important boundary:

- mart-forge is a framework and orchestrator. It scaffolds warehouses and reviews them.
- Domain-specific business logic (trading signals, position sizing, risk management) is out of scope. The framework produces verified numbers; downstream consumers own interpretation.
- A conformance run delivers incrementally through checkpoint PRs. Intermediate checkpoints (e.g., BRD signed but TDD pending) represent progress states, not success states. The conformance exam is complete only when all criteria in Section 15.3 are met. An intermediate checkpoint is a valid saved-state that subsequent work builds on — it is not a claim that the exam is finished.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Produce a **methodology-first, agent-executable DWH harness** that a data PM or data engineer can install and use to deploy a high-quality Kimball warehouse with dashboard.
- Use **GME options analytics** as the canonical conformance examination — proving the framework works against a real domain with live data and verifiable external sources.
- Deliver through **incremental checkpoint PRs** — each lifecycle phase (BRD, ODS, DIM, DWS, ADS, DQC, dashboard) merges independently to `main`. Defects at step N fix step N; prior accepted checkpoints are preserved.
- Enforce **source-native preference**: when a data provider exposes a metric directly, ingest it as a pass-through field. Compute derived metrics only when no provider offers the metric natively. This prevents unnecessary calculation layers that introduce drift from authoritative sources.
- Serve **two audiences**: (a) retail investors and options researchers who consume the live GME dashboard for correct, verifiable analytics; (b) data engineers and data PMs who use the framework to scaffold their own warehouses — targeting broad adoption as an open-source tool.
- Enforce **dogfooding**: every conformance example MUST be built by invoking the framework's own skills in their documented order. Hand-edited artifacts that merely match the template shape do not satisfy conformance. Skill invocations MUST be traceable in the agent's tool-use log.
- Maintain a **single living specification** (this document). Version history lives in git, not in filename proliferation. No `SPEC_V2.md`, no `SPEC_FEEDBACK.md`, no `SPEC_ITERATION_2.md`. If feedback changes the spec, the spec is edited in place.

### 2.2 Non-Goals

- Real-time streaming data pipelines (batch/daily grain only).
- A hosted SaaS product or web UI beyond the Streamlit dashboard.
- Trading signals, financial advice, position sizing, or risk management logic.
- Operator-private analytics (warrant monitoring, position tracking, risk protocols) — these are out of scope for the public framework and belong in separate private repositories.
- Multi-tenant access or user authentication.
- MotherDuck paid-tier features (stay within free tier where possible).
- Replacing dbt — this framework uses dbt as the transform engine, not as a competitor.
- Prescribing a specific cloud provider or data warehouse beyond the reference implementation (dbt-duckdb + MotherDuck).

---

## 3. System Overview

### 3.1 Product Architecture

```
mart-forge/
├── .claude/
│   ├── agents/                  # Declarative agent definitions (file-per-agent, YAML frontmatter)
│   ├── agent-memory/            # Per-agent persistent memory across sessions
│   ├── skills/                  # Methodology skills with hard gates between phases
│   ├── hooks/                   # SessionStart bootstrap + pre-tool guards
│   ├── docs/                    # Agent coordination map, context management rules
│   └── rules/                   # Session-scoped behavioral rules
├── .claude-plugin/
│   └── plugin.json              # One-command install manifest
├── production/
│   └── session-state/
│       └── active.md            # Live orchestrator state (updated every session)
├── templates/
│   ├── business-requirements.template.md
│   ├── tech-design-doc.template.md
│   ├── mart.yml.template
│   ├── models/                  # Per-layer SQL templates (ODS/DIM/DWD/DWS/ADS)
│   ├── seeds/                   # Seed CSV templates
│   ├── tests/                   # Test templates (generic + singular + reconciliation)
│   ├── dashboard/               # Streamlit app template with dual-mode connection
│   └── pipeline/                # GitHub Actions workflow template
├── tests/
│   └── skill-testing/           # Behavioral specs + static linter for framework skills
│       ├── catalog.yaml         # Registry of all skills + agents with coverage tracking
│       ├── quality-rubric.md    # Category-specific pass/fail metrics
│       ├── skills/              # Per-skill behavioral spec files
│       └── agents/              # Per-agent behavioral spec files
├── examples/
│   └── gme-options-mart/        # Canonical conformance exam (only accepted trials land here)
├── docs/
│   ├── METHODOLOGY.md           # Full Kimball 4-tier methodology reference
│   ├── naming-conventions.md    # Table/column/model naming rules
│   ├── bus-matrix.md            # Conformed dimension mapping guide
│   ├── dqc-framework.md         # 8-control DQC catalog reference
│   └── provider-abstraction.md  # How data providers plug into the framework
├── src/
│   └── mart_forge/              # CLI: mart-forge init | tdd | scaffold | validate
├── scripts/
│   ├── dqc_update.py            # Mechanically links dqc_scorecard.json to dbt test results
│   └── confidentiality_scan.py  # CI step: reject commits with banned strings
├── SPEC.md                      # This specification (public-portability version)
├── CLAUDE.md                    # Project rules for agent sessions (@-imported, slim top file)
├── METHODOLOGY.md               # Kimball 4-tier reference (symlinked from docs/)
├── README.md                    # Public-facing landing page
├── pyproject.toml               # Package definition with CLI entry points
└── LICENSE
```

### 3.2 Actors

The framework executes through a tiered agent model:

| Tier | Actor | Role | Model | Authority |
|------|-------|------|-------|-----------|
| 1 | Orchestrator | Owns this SPEC. Dispatches work, reviews gates, classifies ambiguous feedback, approves/rejects deliverables. Does NOT implement. | Opus | Full gate authority; operator-proxy when delegated |
| 2 | Adversarial Reviewer | Grades BRDs, TDDs, and conformance artifacts against this SPEC's quality rubric. Finds gate bypasses and structural defects. | Opus | Grade authority; infinite review iterations until grade A |
| 3 | Implementation Kin | Executes atomic tickets: writes code, templates, tests, docs. One active ticket at a time. Isolated worktrees. One-reviewable-change delivery. | Opus | Autonomous within ticket scope; cannot merge or bypass gates |

Agents are defined declaratively in `.claude/agents/<name>.md` with YAML frontmatter (`name`, `description`, `tools`, `model`, `maxTurns`, `skills`, `memory`) and a prose body containing the collaboration protocol and domain-specific workflow.

### 3.3 Repository Strategy

| Repository | Visibility | Purpose | Status |
|------------|-----------|---------|--------|
| `LongShortNMargin/mart-forge` | **PUBLIC** | The product. Framework on `main`; conformance examples in `examples/`. | Active — branch-protected `main` (require PR + status checks, no force-push) |

Any commit to this repository that contains private document references, operator-specific data, or confidential source identifiers is a **CRITICAL FAILURE** (Section 14).

### 3.4 Orchestration Isolation

Framework development and conformance testing run in separate orchestration projects to prevent cross-contamination:

| Project | Home Directory | Purpose | Agents |
|---------|---------------|---------|--------|
| Private orchestration project | Private orchestration repository | SPEC drafting, harness construction, internal governance | Orchestrator, Reviewer, Implementation Kin |
| Public conformance project | `LongShortNMargin/mart-forge` checkout | Conformance examination. ALL conformance deliverables land here. | Implementation Kin (dispatched by Orchestrator) |

When the harness is built (Phase F complete), conformance tickets MUST run from the public conformance project with their working directory inside the mart-forge checkout. This ensures conformance artifacts are produced in the context of the public repository, not imported from a private one.

### 3.5 External Dependencies

| Dependency | Required | Role |
|------------|----------|------|
| dbt-core + dbt-duckdb | Yes | Transform engine (reference implementation) |
| DuckDB (local) | Yes | Local development and CI warehouse engine |
| MotherDuck | Yes (conformance dashboard) | Live dashboard warehouse target for operator acceptance |
| Python 3.11+ | Yes | Scripts, ingestion adapters, dashboard, CLI |
| Streamlit | Yes (conformance dashboard) | Dashboard presentation layer |
| GitHub Actions | Yes | CI pipeline |
| Multica | Yes | Agent dispatch and orchestration |
| Data provider(s) | Conformance (candidate) | Upstream metric sources are NOT pre-selected. Provider, endpoint, field mappings, and ingestion path bind only through the signed TDD after source discovery. |

### 3.6 Collaboration Protocol

Every agent action follows the collaborative workflow:

```
1. Question    — Agent asks clarifying questions about the task
2. Options     — Agent presents 2-3 approaches with trade-offs
3. Decision    — Reviewer/Orchestrator decides
4. Draft       — Agent produces the deliverable
5. Approval    — Reviewer/Orchestrator reviews and approves ("May I write this to <filepath>?")
```

No file writes without explicit approval. No multi-file changes without changeset approval. No commits without orchestrator instruction. This protocol is enforced by the SessionStart hook and documented in each agent's definition file.

---

## 4. Core Domain Model

### 4.1 Framework Artifact

The primary deliverable of Phase F. A complete, self-contained framework that can scaffold a Kimball DWH from stakeholder input without any domain-specific content.

Fields:
- `templates/` — BRD, TDD, mart.yml, model SQL per layer, seed CSV, test patterns, dashboard skeleton, CI pipeline
- `skills/` — Agent skills with hard gates between lifecycle phases (source-discovery → mart-brd → mart-tdd → mart-bootstrap → mart-dqc → mart-review)
- `tests/skill-testing/` — Behavioral specs and static linter for every skill and agent
- `docs/` — Methodology, naming conventions, bus matrix, DQC framework, provider abstraction
- `.claude-plugin/` + `hooks/` — Plugin manifest for one-command install; SessionStart bootstrap for methodology injection
- `CLAUDE.md` — Project rules for agent sessions, @-imported to keep the top file slim
- `SPEC.md` — This specification (public-portability version)

### 4.2 Conformance Exam

A working mart built *using the framework* (not alongside it) that proves the framework's methodology and tooling produce a trustworthy, verifiable warehouse.

Fields:
- `examples/{exam-name}/` — The accepted conformance output. Only skill-produced, accepted trials land here.
- `mart.yml` — Configuration contract (generated after source discovery + signed TDD, not before)
- `business-requirements.md` — Signed BRD instance (produced by `/mart-brd` skill invocation)
- `tech-design-doc.md` — Signed TDD instance (produced by `/mart-tdd` skill invocation)
- `models/` — dbt models (produced by `/mart-bootstrap` scaffold)
- `seeds/` — Static dimension and fixture data
- `tests/` — DQC tests implementing the control catalog
- `fixtures/` — Static test data with manifest (source date, provider, row count, schema hash)
- `dashboard/` — Streamlit presentation layer with dual-mode connection (MotherDuck live + DuckDB local)
- `dqc_scorecard.json` — Machine-readable quality artifact linked to `dbt test` results
- `coverage_manifest.json` — verified_count / planned_count per metric with per-metric status

### 4.3 Metric Contract

Every metric in a BRD/TDD declares two classifications:

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
| `proxy` | External source provides a related but not identical metric | Advisory comparator link, visibly distinct, labeled "Advisory comparator — not ingestion provenance or DQC truth" | Cannot be used as DQC pass/fail truth |
| `unsupported` | No free external source exists after resource exhaustion (Section 6.3) | "No external comparator available" with evidence reference | Requires `attempts[]` documenting each resource tried |
| `unverified` | Source exists but has not been checked | MUST NOT appear in an accepted dashboard. Blocked at TDD sign-off. | Temporary only; must resolve before sign-off |

### 4.4 BRD (Business Requirements Document)

The first deliverable in a conformance exam. Stakeholder-facing. Produced by `/mart-brd` skill invocation against a source catalog.

Mandatory sections (B-1 through B-4):

| # | Section | Purpose |
|---|---------|---------|
| B-1 | Version History | Track every revision from draft through sign-off |
| B-2 | Business Context | Business process, purpose, stakeholder needs, domain glossary, data sources with verification results (Section 6.1) |
| B-3 | Metrics Breakdown | Every metric with: name, `source_type` (§4.3.1), `link_status` (§4.3.2), public classification, candidate verification evidence |
| B-4 | Notable / Known Limitations | Declared constraints, unsupported metrics with resource-exhaustion evidence (§6.3), known gaps |

### 4.5 TDD (Technical Design Document)

The second deliverable. Technical-facing. Produced by `/mart-tdd` skill invocation after BRD approval.

Mandatory sections (T-1 through T-21):

| # | Section | Purpose |
|---|---------|---------|
| T-1 | Changelog | Track every revision from draft through sign-off |
| T-2 | Business Background | Domain context from BRD, tracing to stakeholder needs |
| T-3 | Metrics Breakdown | Traces every BRD metric to a table + column + source |
| T-4 | Design Consideration | 4-step Kimball method: business process → grain → dimensions → facts |
| T-5 | Bus Matrix | Fact-to-dimension mapping |
| T-6 | Table Summary | Every table (ODS/DIM/DWD/DWS/ADS) with purpose and grain. Every entry traces forward to Schema Detail and Physical Design. |
| T-7 | Data Architecture Diagram | Visual layer-by-layer flow: source → ODS → DIM → DWD → DWS → ADS |
| T-8 | Table Schema Detail | Column-level spec per table: `column_name \| data_type \| definition \| example_value \| calculation \| data_source`. `calculation` MUST contain actual SQL/formula for derived columns and pass-through field mapping for native columns. |
| T-9 | ODS Table Columns | Per table: source, grain, logical partition, `incremental_strategy`, `unique_key`, backfill, restatement, provenance columns (Section 7.4) |
| T-10 | DIM Table Columns | Conformed dimensions; seed-backed where applicable. Column-level spec per §T-8 format. |
| T-11 | DWD Table Columns | Cleaned facts with business keys. Native: pass-through. Derived: explicit SQL in `calculation`. |
| T-12 | Count DWS Table Columns | Count-type aggregations (row counts, event counts) with explicit SQL per `calculation` column |
| T-13 | Performance DWS Table Columns | Performance/ratio aggregations (rates, averages, percentiles) with explicit SQL per `calculation` column |
| T-14 | ADS / Presentation Table Columns | Application-facing one-big-tables; metric-to-column traceability to upstream DWS/DWD |
| T-15 | Physical Design | Column-level spec for every table type. Coverage MUST span all tables in Table Summary (T-6). |
| T-16 | Coding | Implementation spec: dbt model naming, materialization strategy, `ref()` chain, Jinja patterns, macro usage |
| T-17 | Dashboard Specification | Visualization list: chart type + data source model + link-status display rule per metric. Fixture/live mode behavior. Coverage badge rendering. This section is the signed contract that Checkpoint 5 validates against. |
| T-18 | DQC Plan | Controls per §8.2 applicability matrix. Control class, metric, severity, applicable source type. `not_applicable` entries with rationale for controls that don't apply. |
| T-19 | Test Case | Test inventory: test name, type (generic / singular / reconciliation), target model, expected result. Maps every DQC control to an executable test. |
| T-20 | Job Monitoring and Alerts | Refresh schedule, SLA, timezone, alerting channels, failure handling, holiday behavior |
| T-21 | Notable / Known Limitations | Declared constraints, unsupported metrics with resource-exhaustion evidence (§6.3), known data gaps |

The TDD section list matches the established warehouse design-document standard at one-to-one section parity. Count DWS and Performance DWS are separate sections (not merged). DQC Plan and Test Case are separate sections (not merged). Job Monitoring and Notable are separate sections (not merged). Any table type required by the design but absent from the TDD requires a signed `not_applicable` rationale.

### 4.6 Checkpoint PR

An incremental, reviewable delivery unit. Each lifecycle phase produces one checkpoint PR targeting `main`. Checkpoints are independent saved-states: a defect at checkpoint N does NOT invalidate checkpoints 1 through N-1.

Fields:
- `phase` — which lifecycle phase this checkpoint represents (BRD/TDD, ODS, DIM/FACT, DWS, ADS/dashboard, DQC)
- `branch` — feature branch name following `<project>/<phase-slug>` convention
- `artifacts` — list of files added/modified
- `ci_status` — GitHub Actions result
- `review_status` — Copilot clean + orchestrator/reviewer verdict
- `merge_status` — merged to `main` or pending

### 4.7 Coverage Manifest

Machine-readable progress artifact tracking verified metric coverage.

Fields per metric:
- `name` — metric identifier from BRD
- `source_type` — native / derived / hybrid
- `link_status` — exact / proxy / unsupported
- `status` — verified / proxy / stale / unsupported / unverified / failed
- `last_verified_ts` — ISO-8601 timestamp of last successful verification
- `last_failure_reason` — if status is failed/stale
- `playwright_evidence_uri` — path to browser verification evidence
- `dqc_test_refs` — linked dbt test names

Aggregates:
- `planned_count` — total metrics in BRD
- `verified_count` — metrics with status = verified
- `coverage_pct` — verified_count / planned_count

### 4.8 Classification Ledger

A private artifact maintained in the orchestration repository's copy of this SPEC (Appendix A). The public-portability `SPEC.md` in `LongShortNMargin/mart-forge` MUST NOT include the ledger content — it carries only the schema definition below. Actual ledger entries are private operational records.

Fields per entry:
- `timestamp` — ISO-8601
- `source` — who/what produced the feedback
- `raw_feedback` — verbatim text
- `classification` — what the feedback means for the framework (contract issue vs implementation issue)
- `ruling` — action taken (checkpoint rollback, harness revision, escalation)
- `override_trail` — if the human operator later overrides, record here

---

## 5. Lifecycle and State Machine

### 5.1 Program Phases

```
SPEC approved ──► Phase F (framework on main) ──► Phase G (conformance exam)
                                                       │
                                            ┌──────────┴──────────────┐
                                            │  Checkpoint PR Loop      │
                                            │                          │
                                            │  BRD + TDD → PR → ACCEPT │
                                            │       ↓                  │
                                            │  source-discovery + ODS  │
                                            │       → PR → QC          │
                                            │       ↓                  │
                                            │  DIM + FACT → PR → ACCEPT│
                                            │       ↓                  │
                                            │  DWS → PR → ACCEPT      │
                                            │       ↓                  │
                                            │  ADS + dashboard         │
                                            │       → PR → ACCEPT      │
                                            │       ↓                  │
                                            │  DQC + scorecard         │
                                            │       → PR → ACCEPT      │
                                            └──────────────────────────┘
```

### 5.2 Phase F — Framework Construction

**Objective:** Build the framework product on `main` with zero domain-specific content.

**Deliverables:**
- All templates (BRD, TDD, mart.yml, model SQL per layer, seeds, tests, pipeline, dashboard)
- All skills (using-mart-forge, source-discovery, mart-brd, mart-tdd, mart-bootstrap, mart-dqc, mart-review)
- Plugin harness (`.claude-plugin/plugin.json`, `hooks/hooks.json`)
- Skill Testing Framework (`tests/skill-testing/` with catalog, rubric, behavioral specs)
- Documentation (METHODOLOGY.md, CLAUDE.md, naming-conventions, bus-matrix, dqc-framework, provider-abstraction)
- CI pipeline (framework-level tests, confidentiality scan, skill-test static all)
- SPEC.md (this document, public-portability version)

**Acceptance:**
- `main` contains a complete, self-contained framework with zero domain-specific content
- Plugin installs and SessionStart hook fires
- All skills have hard gates enforced (no scaffold without signed TDD; no TDD without signed BRD)
- `/skill-test static all` passes
- A data engineer can read templates/docs and understand how to build a mart without a conformance example
- CI green including confidentiality scan

### 5.3 Phase G — Conformance Examination (Incremental Checkpoints)

**Objective:** Validate the framework against the GME options domain using the framework's own skills.

**Gate:** Phase F MUST be complete and accepted before any Phase G work begins.

**G-DOGFOOD requirement:** Every conformance artifact MUST be produced by invoking the framework's own skills in their documented order. Skill invocations MUST be traceable in the agent's tool-use log. Hand-edited content that merely matches the template shape does not satisfy conformance.

#### 5.3.1 Checkpoint 1 — BRD + TDD

**Work in:** Feature branch from `main` via the public conformance project.

**Process:**
1. Invoke `/source-discovery` against the stakeholder input document. Verify each candidate: availability, asset identity, license/terms, freshness, semantic match (Section 6).
2. Invoke `/mart-brd` to produce a BRD from the source catalog. Every non-DWS (non-derived) metric MUST NOT be empty or unavailable — this is a literal acceptance requirement.
3. Reviewer grades BRD → grade A required.
4. Invoke `/mart-tdd` to produce a TDD from the signed BRD.
5. Reviewer grades TDD → grade A required.
6. Checkpoint PR → merge to `main`.

#### 5.3.2 Checkpoint 2 — Source Discovery + ODS

**Precondition:** Checkpoint 1 merged.

**Process:**
1. Implement ODS ingestion models per the signed TDD's ODS contract (§7.3).
2. Verify: incremental strategy works, idempotence test passes (run twice, row counts don't double).
3. Quality check against signed TDD — every ODS column matches the T-9 specification.
4. Checkpoint PR → merge to `main`.

#### 5.3.3 Checkpoint 3 — DIM + DWD (Facts)

**Precondition:** Checkpoint 2 merged.

**Process:**
1. Implement dimension and fact models per signed TDD (T-10, T-11).
2. Verify: FK integrity, grain discipline, business key uniqueness.
3. Checkpoint PR → merge to `main`.

#### 5.3.4 Checkpoint 4 — DWS (Aggregations)

**Precondition:** Checkpoint 3 merged.

**Process:**
1. Implement DWS aggregation models per signed TDD (T-12 Count DWS, T-13 Performance DWS).
2. Verify: derived metrics match TDD SQL, window functions correct, trailing aggregations produce expected shapes.
3. Checkpoint PR → merge to `main`.

#### 5.3.5 Checkpoint 5 — ADS + Dashboard

**Precondition:** Checkpoint 4 merged.

**Process:**
1. Implement ADS one-big-table per signed TDD (T-14 ADS, T-15 Physical Design).
2. Build dashboard from signed TDD Dashboard Specification (T-17). Real visualizations (not metric-cards-only). Dual-mode connection: MotherDuck live + DuckDB local. Every visualization in T-17 MUST be implemented.
3. Link-status display rules (Section 8.5): exact → verified link, proxy → advisory comparator, unsupported → "no comparator available".
4. Coverage manifest generated and rendered as dashboard badge.
5. Checkpoint PR → merge to `main`.

#### 5.3.6 Checkpoint 6 — DQC + Scorecard

**Precondition:** Checkpoint 5 merged.

**Process:**
1. Implement DQC controls per Section 8.2 applicability matrix.
2. `dqc_scorecard.json` mechanically generated from `target/run_results.json`.
3. Freshness enforcement in CI.
4. All controls pass or carry documented `attempts[]` for non-pass statuses.
5. Checkpoint PR → merge to `main`.

### 5.4 Checkpoint Rollback Rules

Defects discovered at checkpoint N are handled locally:

- **Defect in checkpoint N's own artifacts:** Fix on a new branch from `main`, produce a corrected checkpoint PR. Prior checkpoints (1..N-1) are NOT re-done.
- **Defect traceable to an earlier checkpoint (e.g., BRD metric definition is wrong):** Go back to THAT checkpoint specifically. Produce a corrected checkpoint PR for that phase. Subsequent checkpoints may need reconciliation but are not automatically invalidated.
- **Defect traceable to the framework (harness bug, template defect, skill logic error):** Return to Phase F. Fix the framework on `main`. Then re-run the affected Phase G checkpoint through the revised framework — delete the prior conformance artifact and rebuild via skill invocation (the destruct-regenerate sub-loop).

### 5.5 Phase F Harness-Quality Loop

Phase F runs CONTINUOUSLY alongside Phase G, never as a shield gate:

```
each Phase F iteration:
  1. Identify the harness defect (surfaced by Phase G checkpoint failure,
     adversarial review finding, or coverage regression)
  2. Fix the harness defect on main (template, skill, gate logic, scaffold,
     DQC pattern, dashboard component)
  3. Delete the affected conformance artifact from examples/
  4. Invoke the framework's own skills to REBUILD the artifact (G-DOGFOOD)
  5. DQC check: every source maps to a metric; every metric maps back to BRD/TDD
  6. If step 5 fails → harness gap → return to step 2
  7. Coverage manifest: verified_count / planned_count MUST rise or a labelled
     defect MUST resolve. Iterations that accomplish neither require orchestrator
     justification in the Classification Ledger.
```

**Three-strike escalation rule (applies to ALL checkpoints, not just BRD/TDD):** If any single checkpoint sees three failed attempts (one initial + two retries), escalate to the orchestrator (or human operator if available) before any fourth attempt. This applies to every checkpoint (1 through 6), not only to signed-contract regenerations. The orchestrator MUST classify the failure per §10.2 before authorizing further work.

---

## 6. Source Discovery and Metric Contract

### 6.1 Source Selection Principle

Source selection is NOT predetermined. Historical provider failures are risk inputs, not decisions. For each metric candidate, the executing agent MUST verify:

| Check | Question | Fail Action |
|-------|----------|-------------|
| Availability | Does the provider API/endpoint respond from the executing environment? | Try next provider |
| Asset Identity | Does the response contain the correct asset (e.g., GME, not SPY)? | Reject source — wrong-asset CANNOT be `exact` |
| License/Terms | Is the data usable under the repository's license? Redistribution restrictions? | Document restriction |
| Freshness/SLA | Is the data delayed ≤24h for a daily-grain mart? Compatible refresh schedule? | Document SLA gap |
| Semantic Match | Does the provider's field definition match the BRD metric definition? | Cannot be `exact`. Record `proxy` only if explicitly useful and labelled advisory; otherwise `rejected`. |

### 6.2 Browser-Based Link Verification (G-LINK)

Every claimed external comparison link MUST be verified with browser automation before BRD/TDD sign-off.

Per-candidate verification record:

| Field | Description |
|-------|------------|
| `url` | The exact URL tested |
| `capture_timestamp` | ISO-8601 timestamp |
| `rendered_asset_identity` | Asset/ticker shown on the rendered page |
| `rendered_metric_identity` | Specific metric or comparison value shown |
| `candidate_result` | `exact_match` / `advisory_proxy` / `rejected` |

**Classification rules:**
- Wrong asset (e.g., SPY page for a GME mart) → `rejected`. Never `exact_match`, never `advisory_proxy`.
- Correct asset, different metric → `advisory_proxy` only if the comparison is explicitly useful and clearly labelled; otherwise `rejected`.
- `exact_match` requires: correct asset identity + correct metric identity + same methodology + browser evidence confirming all three.

**Resolving metric-level `link_status` from candidate results:**
- Any candidate `exact_match` → metric `link_status` = `exact`
- No `exact_match` but at least one `advisory_proxy` → metric `link_status` = `proxy`
- All candidates `rejected` AND §6.3 resource-exhaustion complete → metric `link_status` = `unsupported`
- Untested candidates remain → metric stays `unverified` (blocked at TDD sign-off)

### 6.3 Resource Exhaustion Protocol

Before any DQC control can be marked `unsupported`, the agent MUST:

1. Enumerate all available resources from the BRD + candidate source inventory + stakeholder input.
2. Attempt each resource and document: source name, result (`pass` / `blocked` / `error`), reason, date, evidence URI, provider version, reproducible command.
3. Only after ALL resources are attempted with documented evidence can `unsupported` status be assigned.
4. The `dqc_scorecard.json` schema MUST include an `attempts[]` array for every non-`pass` control.

### 6.4 Source-Discovery Acceptance Criteria

**Literal requirement:** All non-DWS metrics (source-discoverable metrics that do NOT require derived computation from other mart layers) MUST NOT be empty or unavailable as a result of the `/source-discovery` skill execution. If a provider exists for a metric, that metric MUST have a non-empty source binding in the BRD.

This means:
- Spot price MUST have a confirmed source (not "provider TBD").
- IV30 MUST have a confirmed source if any provider exposes implied volatility natively.
- Max pain may be `derived` (computed from OI cross-join) — that's acceptable because it genuinely requires calculation.
- A metric marked `unsupported` MUST have the §6.3 exhaustion evidence, not a bare "paywalled" waiver.

---

## 7. BRD/TDD Design Contract

### 7.1 Structural Standard

The BRD and TDD templates MUST match the established warehouse design-document standard at 95%+ section coverage. The standard requires:

- **BRD:** Business background, metrics catalog with per-metric classification, domain glossary, verified data sources, stakeholder needs, cycle/cadence model, known limitations.
- **TDD:** Changelog, business context, metrics breakdown, 4-step Kimball design consideration, bus matrix, table summary, data architecture diagram, column-level schema detail with the 6-column format (`column_name | data_type | definition | example_value | calculation | data_source`), ODS/DIM/DWD/DWS/ADS column sections, physical design, coding specification, DQC plan with test cases, job monitoring + alerts, notable/known limitations.

The `calculation` column MUST contain:
- **For native columns:** `pass-through from <provider.field>`
- **For derived columns:** Actual SQL/formula. No "derived", "computed", or "see model" placeholders.
- **For hybrid columns:** Both the native component reference and the derivation formula, with reconciliation tolerance.

### 7.2 BRD Template Requirements

The BRD template (`templates/business-requirements.template.md`) MUST include all sections B-1 through B-4 (Section 4.4). Additional validation rules:

| Aspect | Validation |
|--------|-----------|
| Every metric in B-3 | Has `source_type` + `link_status` + public classification |
| Every data source in B-2 | Has verification results from §6.1 checks — no source asserted without verification |
| B-4 (Notable) | Every `unsupported` metric has §6.3 exhaustion evidence |
| Source-discovery acceptance | All non-DWS metrics MUST NOT be empty/unavailable (§6.4) |

### 7.3 TDD Template Requirements

The TDD template (`templates/tech-design-doc.template.md`) MUST include all sections T-1 through T-21 (Section 4.5). Additional validation rules:

| Aspect | Validation |
|--------|-----------|
| T-4 (Design Consideration) | All 4 Kimball steps present and non-empty |
| T-5 (Bus Matrix) | ≥1 fact and ≥1 dimension mapped |
| T-8 (Schema Detail) | Every column has all 6 fields; `calculation` has actual SQL for derived |
| T-9 (ODS) | Every ODS table has: source, grain, logical partition, `incremental_strategy`, `unique_key`, backfill variable(s), restatement behavior, provenance columns. Idempotence verification required. |
| T-6 (Table Summary) | Every entry traces forward to a T-8 Schema Detail entry AND a T-15 Physical Design section |
| T-15 (Physical Design) | Coverage spans ALL table types in Table Summary |
| T-18 (DQC Plan) | Controls per §8.2 applicability matrix; non-applicable controls documented with rationale |

### 7.4 ODS Table Contract

Every ODS table in a daily-grain mart MUST define:

| Field | Description | Example |
|-------|------------|---------|
| `source` | Provider + endpoint/method | *(Bound by signed TDD; not pre-selected)* |
| `grain` | One row represents... | `One option contract on one pull date` |
| `logical_partition` | Column for incremental windowing | `pull_date` |
| `incremental_strategy` | Valid dbt-duckdb strategy | `delete+insert` |
| `unique_key` | Deduplication composite | `['pull_date', 'option_symbol']` |
| `backfill` | How to load historical data | `dbt run --vars '{pull_date: "2026-05-01"}'` |
| `restatement` | Behavior when source data is corrected | `Re-run for the affected pull_date; delete+insert replaces` |
| `provenance_columns` | Audit trail fields | `provider, pull_ts_utc, quote_ts_utc, run_id` |

Idempotence: running the same pull_date twice MUST produce identical output. CI MUST include a rerun idempotence test.

### 7.5 Grade Gates

Two mandatory grade gates per conformance exam:

- **G-BRD:** Adversarial reviewer grades the BRD. Grade A required. No TDD until BRD reaches grade A. Waiver requires orchestrator stamp with documented rationale in the Classification Ledger.
- **G-TDD:** Adversarial reviewer grades the TDD. Grade A required. No scaffold until TDD reaches grade A. Same waiver rules.

Neither gate may be skipped. Adversarial review has no iteration budget cap — the reviewer continues until grade A is reached or the framework is identified as deficient.

### 7.6 Design Package Validation

The signed BRD/TDD package MUST be rejected if it exhibits any of:

1. **Missing mandatory section.** Any section from §4.4 (BRD) or §4.5 (TDD) absent.
2. **Table type omitted without rationale.** Every table type in the design (ODS, DIM, DWD, DWS, ADS) MUST have its corresponding column section. If not required, a signed `not_applicable` rationale is REQUIRED.
3. **Metric without end-to-end traceability.** Every BRD metric (B-3) MUST trace through: source discovery evidence → TDD table column → TDD physical design → signed dashboard specification.
4. **Table-summary-to-schema-detail gap.** Every table in T-6 MUST have a T-8 entry AND a T-15 entry. Unmatched entries fail the gate.
5. **Unresolved `link_status`.** Any metric with `unverified` at TDD sign-off fails the gate.

---

## 8. Scaffold / DQC / Dashboard Contract

### 8.1 Scaffold Output

Phase C (scaffold from signed TDD) MUST produce the standard directory structure:

```
examples/{exam-name}/
├── mart.yml                    # Configuration contract
├── business-requirements.md    # Signed BRD (from Checkpoint 1)
├── tech-design-doc.md          # Signed TDD (from Checkpoint 1)
├── models/
│   ├── ods/                    # Incremental ingestion
│   ├── dim/                    # Conformed dimensions (seed-backed)
│   ├── dwd/                    # Cleaned facts with business keys
│   ├── dws/                    # Aggregations, rollups, windows
│   └── ads/                    # Application-facing one-big-tables
├── seeds/                      # Static CSVs (dim_date, dim_instrument)
├── tests/                      # Generic + singular + reconciliation
├── fixtures/                   # Static test data with manifest
├── dashboard/
│   ├── app.py                  # Streamlit with dual-mode connection + link-status display
│   ├── requirements.txt
│   └── README.md               # Connection instructions
├── dqc_scorecard.json          # Machine-readable quality artifact
├── coverage_manifest.json      # Verified metric coverage tracking
├── dbt_project.yml
├── profiles.yml
└── .github/workflows/daily.yml # CI pipeline
```

### 8.2 DQC Control Catalog

Eight control classes. Applicability is scoped per table, metric, and source type — not every control applies to every table.

| # | Control Class | Checks | Severity | Applicability |
|---|---------------|--------|----------|---------------|
| 1 | PK Integrity | PK not null + unique | `error` | All tables |
| 2 | FK Integrity | FK resolves to DIM row | `error` | Tables with foreign keys only |
| 3 | Freshness | Most recent `pull_ts_utc` within SLA | `error` | ODS/DWD tables |
| 4 | Completeness / Volume | Row count within expected range vs prior run | `warn` | Tables with regular refresh |
| 5 | Accepted Ranges | Numeric metrics within plausible bounds | `warn` | Native + derived numeric metrics |
| 6 | Duplicate Detection | No duplicate business keys within grain window | `error` | All fact tables |
| 7 | Null-Rate Threshold | Non-PK columns under configured null percentage | `warn` | All tables (threshold per column) |
| 8 | Business Reconciliation | Key metrics match external source within tolerance | `error`/`warn` | Only when an `exact` external comparator exists |

**Applicability by source type:**
- `native`: PK integrity, provenance, freshness, pass-through field checks. No formula tests.
- `derived`: PK integrity, formula/business logic tests, accepted ranges. Explicit SQL validation.
- `hybrid`: PK integrity, provenance, formula tests, documented reconciliation with tolerance.

Controls not applicable to a table/metric carry a `not_applicable` entry with rationale in the scorecard.

### 8.3 Scorecard Linkage

The `dqc_scorecard.json` MUST be mechanically generated from `target/run_results.json` after `dbt test`. A `dqc_update.py` script reads test results and updates scorecard statuses. The scorecard MUST NOT be stale versus actual test outcomes.

Schema requirements:
- Each control entry includes `linked_dbt_tests[]` referencing test names.
- Each control entry includes `last_dbt_run` timestamp.
- Non-pass controls include `attempts[]` per §6.3.
- `unsupported`, `unverified`, `pending`, or `failed` statuses are NEVER displayed as green/pass.

### 8.4 Fixture and Live Mode Separation

| Mode | Data Source | Where Used | Display Rule |
|------|-----------|-----------|-------------|
| Fixture/demo | Static parquet/CSV with manifest | CI, local dev | Dashboard MUST show explicit "FIXTURE/DEMO" banner. Never claim fixture is live. |
| Live/operator | MotherDuck populated from approved sources | Production | Dashboard pulls from MotherDuck. Displays "BLOCKED/STALE" if data unavailable — never substitutes fixture silently. |

The fixture manifest MUST include: source date, source URL/provider, captured value, row count, schema hash.

### 8.5 Dashboard Contract

The dashboard MUST:
- Include useful visualizations from the signed TDD dashboard spec — not metric-cards-only.
- Consume DQC results and provenance — never ask users to key reference values manually.
- Display external comparison links per link_status:
  - `exact` → verification link icon labeled "Exact verification source"
  - `proxy` → visibly distinct advisory comparator labeled "Advisory comparator — not ingestion provenance"
  - `unsupported` → "No external comparator available" with evidence reference
  - `unverified` → MUST NOT appear in an accepted dashboard (blocked at TDD sign-off)
- Distinguish fixture mode from live mode visually.
- Render the coverage manifest as a dashboard badge: `Data Loaded N/M | DQC Verified N/M`.
- Trace every metric to a TDD entry (bidirectional traceability).

MotherDuck credentials are environment-sourced (`MOTHERDUCK_TOKEN`) and NEVER committed.

---

## 9. Quality Gates

Every gate MUST pass before its gated phase can proceed. Gates are checked by the adversarial reviewer or CI; the orchestrator records the verdict.

| Gate | Description | Applies To | Enforcement |
|------|-------------|-----------|-------------|
| G-SPEC | This specification reviewed by adversarial reviewer and approved by orchestrator | Program level | Blocks all repo work until approved |
| G-BRD | Adversarial reviewer grade A on BRD | Per conformance exam (Checkpoint 1) | No TDD without grade A BRD |
| G-TDD | Adversarial reviewer grade A on TDD | Per conformance exam (Checkpoint 1) | No scaffold without grade A TDD |
| G-LINK | All candidate comparison links browser-verified per §6.2; metric-level `link_status` resolved | BRD/TDD (Checkpoint 1) | Unverified metrics blocked at TDD sign-off |
| G-FIXTURE | Fixture data labeled with manifest; no fixture presented as live | Implementation | CI check + dashboard banner enforcement |
| G-ODS | Every ODS table satisfies §7.4 (source/partition/incremental/unique_key/backfill/restatement/provenance). Idempotence test green. | TDD + Implementation | Checkpoint 2 acceptance criteria |
| G-DOGFOOD | Conformance example built by invoking framework's own skills. Skill invocations recorded in `examples/{exam-name}/.dogfood-log.jsonl` with schema `{timestamp, skill_name, input_artifact, output_artifact, checkpoint}`. CI step validates: (a) log exists, (b) every checkpoint artifact has a corresponding entry, (c) no artifact exists without a skill-invocation entry. Behavioral spec in Skill Testing Framework validates end-to-end. | Phase G (all checkpoints) | CI enforcement via `scripts/validate_dogfood.py` + Skill Testing Framework behavioral spec for `mart-bootstrap` |
| G-HONEST-LABEL | No metric on dashboard shows a value without its status badge. Non-verified statuses use visibly distinct presentation. Silent fixture/proxy/stale substitution = CI-blocking defect. | Dashboard (Checkpoint 5) | CI check + dashboard rendering validation |
| G-ITERATIVE | Each Phase F iteration measurably raises `coverage_pct` or resolves a labelled defect or upgrades a degraded status. Iterations accomplishing none require Classification Ledger justification. | Phase F loop | Orchestrator enforcement |
| G-CI | GitHub Actions green on `main` after each checkpoint merge | All checkpoints | Branch protection rule |
| G-MERGE | Every PR: reviewer has no blocking comments AND CI green. No merge without both. | All phases | Branch protection + review requirement |
| G-CONFIDENTIAL | Zero operator-position data, zero private paths, zero internal project identifiers, zero confidential methodology names in the public repository. **Any violation = CRITICAL FAILURE.** | ALL commits to `LongShortNMargin/mart-forge` | CI confidentiality scan (`scripts/confidentiality_scan.py`) |
| G-CORRECT | Inaccurate values are NEVER acceptable. Coverage growth from relaxing verification (skipping browser checks, asserting links without evidence, suppressing DQC) = CI-blocking defect. | All phases | Adversarial review probe |

---

## 10. Failure and Recovery

### 10.1 Checkpoint-Level Rollback

Defects at checkpoint N are scoped to that checkpoint:

| Defect Location | Action | Prior Checkpoints |
|----------------|--------|-------------------|
| Checkpoint N's own artifacts | Fix on a new branch, produce corrected checkpoint PR | KEPT (1..N-1 untouched) |
| Earlier checkpoint (e.g., BRD metric wrong) | Go back to THAT checkpoint, produce corrected PR for that phase | Later checkpoints may need reconciliation but are NOT auto-invalidated |
| Framework defect (template, skill, gate logic) | Return to Phase F. Fix framework on `main`. Delete affected conformance artifact. Rebuild via skill invocation (§5.5 destruct-regenerate). | ALL conformance checkpoints re-evaluated against revised framework |

### 10.2 Three-Strike Escalation

One initial attempt plus two failed retries (three total) on ANY checkpoint triggers escalation to the orchestrator (or human operator if available) before any fourth attempt. This applies to:
- Signed BRD/TDD contract regenerations (Checkpoint 1).
- ODS implementation retries (Checkpoint 2).
- DIM/DWD, DWS, ADS/Dashboard, DQC retries (Checkpoints 3-6).

The orchestrator MUST classify the failure as:

- **Framework viability issue** — the framework cannot produce a correct result from this contract. Requires contract revision (new BRD/TDD).
- **Implementation variance** — the framework works but the kin's execution is incorrect. Requires different kin or more specific instructions.
- **Source availability issue** — the framework and kin are correct but data providers are unreachable. Requires environment remediation.

### 10.3 Human Operator Override

The human operator MAY override any ruling at any time:
- Override of a rejection → work continues from current state.
- Override of an approval → work product is voided; reset to appropriate phase.
- All overrides recorded in the Classification Ledger (§4.8) override trail.

---

## 11. Coordination and Workspace Safety

### 11.1 Concurrency Rule

One active implementation ticket at a time per agent. The implementation kin does not run concurrent tickets. The adversarial reviewer may run concurrent grading tasks, but only one implementation worktree is active.

### 11.2 Worktree Isolation

- All implementation work happens in isolated worktrees, never in a shared checkout.
- Worktree paths follow: `/tmp/mart-forge-<ticket-slug>/` for conformance work.
- If a worktree branch or path already exists or is dirty, the agent MUST report the conflict and choose a new path. Never reset or delete existing work.
- At completion, commit only the specified deliverables on the worktree branch.

### 11.3 Orchestration Dispatch

All implementation and artifact-writing work MUST be dispatched through the orchestration platform. The orchestration platform may internally choose its runtime; the restriction is on bypassing the dispatch layer, not the runtime it selects.

Read-only orchestrator consultation remains permitted outside dispatch for gate sign-off, rejection classification, and requirements clarification. These consultations do not produce implementation artifacts.

### 11.4 Collaboration Protocol

Every agent follows the 5-step collaborative workflow (§3.6): Question → Options → Decision → Draft → Approval. This applies to EVERY task regardless of perceived simplicity. Agents MUST ask before writing files. Multi-file changes require explicit changeset approval.

### 11.5 Project Isolation

| Phase | Orchestration Project | Home Directory | Rule |
|-------|----------------------|---------------|------|
| Phase F (framework) | Private orchestration project | Private orchestration repository | Framework artifacts land in `LongShortNMargin/mart-forge` via PRs |
| Phase G (conformance) | Public conformance project | `LongShortNMargin/mart-forge` checkout | ALL conformance work executes from inside the public repo. No cross-contamination with private repos. |

The public conformance project is created AFTER Phase F is complete. Its working directory MUST be the mart-forge checkout. Conformance tickets MUST NOT reference files outside the mart-forge repository.

---

## 12. Skill Testing Framework

Adapted from the agent architecture testing framework pattern. Rebranded for the DWH domain.

### 12.1 Structure

```
tests/skill-testing/
├── catalog.yaml           # Registry: all skills + agents, coverage tracking
├── quality-rubric.md      # Category-specific pass/fail metrics
├── skills/                # Per-skill behavioral spec files
│   ├── lifecycle/         # source-discovery, mart-brd, mart-tdd, mart-bootstrap
│   ├── quality/           # mart-dqc, mart-review
│   └── utility/           # using-mart-forge, schema-evolve
├── agents/                # Per-agent behavioral spec files
│   ├── orchestrator.md
│   ├── reviewer.md
│   └── implementer.md
└── results/               # Test run outputs (gitignored)
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

- **`/skill-test static <name>`** — runs structural compliance checks against the spec.
- **`/skill-test static all`** — checks all registered skills. MUST pass in CI.
- **`/skill-test <name>`** — runs the full behavioral spec (requires fixture inputs).
- **G-DOGFOOD enforcement:** The `mart-bootstrap` behavioral spec asserts that a fixture BRD/TDD produces expected scaffold output. If the scaffold doesn't match, the skill is broken — the conformance exam cannot be built.

### 12.4 Adversarial Probe Cases

Every signed-contract gate (BRD approval, TDD approval, scaffold acceptance) MUST have adversarial probe cases in its behavioral spec:

- **Grade bypass:** Remove `Grade: A` from both docs; `APPROVED` alone should NOT pass.
- **Empty binding bypass:** Remove all metric-to-column mappings; scaffold should REJECT.
- **Bogus classification:** Set `link_status: bogus`; validator should REJECT.
- **Contract/output mismatch:** Sign a contract for metric X; scaffold should produce metric X, not a hard-coded default.

These probes are the structural enforcement of G-DOGFOOD. A scaffold that passes its own unit tests but accepts any of these probe inputs does not gate.

---

## 13. Observability

### 13.1 Coverage Manifest

The `coverage_manifest.json` (§4.7) is the program's primary progress metric. It MUST be:
- Mechanically generated (not hand-edited).
- Rendered as a dashboard badge: `Data Loaded N/M | DQC Verified N/M`.
- Updated on every checkpoint merge.
- Consistent with the dashboard's rendered statuses (CI guard: manifest counts MUST match rendered badge).

### 13.2 Checkpoint Traceability

Each checkpoint PR MUST include:
- Commit SHA on the feature branch.
- List of artifacts produced.
- Gate verdicts (G-BRD, G-TDD, G-CI, etc.) with timestamps.
- Reviewer grade and findings summary.
- Link to the orchestration issue where results are posted.

### 13.3 Classification Ledger

The Classification Ledger (§4.8) records every ruling on ambiguous feedback:
- Timestamp, source, raw feedback, classification, ruling, override trail.
- The ledger content is private — it lives ONLY in the orchestration repository's copy of this SPEC (Appendix A). The public `SPEC.md` in `LongShortNMargin/mart-forge` includes the ledger SCHEMA (§4.8 field definitions) but NOT the populated entries. This separation ensures the public SPEC teaches the process without exposing operational rulings.

### 13.4 Program Ledger

A human-readable status surface maintained alongside this SPEC. It MUST be updated when:
- A gate state changes (draft → reviewed → approved).
- A phase state changes (pending → in_progress → complete).
- A checkpoint merges or is rejected.
- A blocker is recorded or resolved.

---

## 14. Trust and Confidentiality

### 14.1 Confidentiality Boundary

`LongShortNMargin/mart-forge` is a **PUBLIC** repository. The following rules are **non-negotiable**:

**MUST NOT appear in any commit, any branch, any file in the mart-forge repository:**
- Operator-specific data: position quantities, cost basis, account identifiers, tactical trading rules, risk protocol parameters
- Private file paths: Google Drive paths, local user paths (`/Users/...`), private repository paths
- Internal project identifiers: names of private projects, internal agent identifiers (e.g., specific agent persona names), internal repository names
- Confidential methodology names: names of proprietary reference documents, proprietary company names, proprietary template standards
- Competitor framing: positioning against named competitors (credit inspiration generically if needed)

**Any violation is a CRITICAL FAILURE.** The commit MUST be reverted. The branch MUST be cleaned. The CI confidentiality scan (`scripts/confidentiality_scan.py`) MUST reject the commit before it reaches `main`.

### 14.2 CI Confidentiality Scan

A mandatory CI step that scans every changed file for banned strings. The scan:
- Runs on every PR targeting `main`.
- Fails the PR if any banned string is detected.
- Reports the file, line, and matched pattern.
- Cannot be bypassed by any agent.

Banned string categories: operator holdings/positions, private file paths, internal project names, confidential document names, proprietary company references.

### 14.3 Trust Posture

| Action | Gate |
|--------|------|
| Code changes in worktrees | Autonomous (within ticket scope) |
| Orchestration ticket management | Autonomous |
| CI-only operations | Autonomous |
| Merge to `main` | Requires reviewer approval + CI green (branch protection) |
| Checkpoint sign-off | Requires adversarial reviewer grade A + orchestrator approval |
| Credential handling | Environment-sourced only; NEVER committed |
| Destructive operations (force-push, branch delete, DB drop) | Requires human operator approval |
| Public-facing content review | Requires orchestrator approval + confidentiality scan |

---

## 15. Validation Matrix

### 15.1 Phase F Acceptance

Phase F is accepted when:
- [ ] `main` contains complete framework (templates, skills, docs, plugin, hooks, CLAUDE.md, SPEC.md)
- [ ] Zero domain-specific content on `main`
- [ ] Plugin installs and SessionStart hook fires
- [ ] All skills have hard gates enforced
- [ ] `/skill-test static all` passes
- [ ] CI green including confidentiality scan
- [ ] A data engineer can understand how to build a mart from templates/docs alone

### 15.2 Per-Checkpoint Acceptance

| Checkpoint | Acceptance Criteria |
|-----------|---------------------|
| 1 (BRD+TDD) | BRD grade A, TDD grade A, all non-DWS metrics have source bindings (§6.4), browser-verified links, `coverage_manifest.json` generated |
| 2 (ODS) | ODS models match T-9 spec, incremental strategy works, idempotence test passes, provenance columns present |
| 3 (DIM+DWD) | FK integrity, grain discipline, business key uniqueness, columns match T-10/T-11 |
| 4 (DWS) | Derived metrics match TDD SQL, window functions correct, aggregations produce expected shapes |
| 5 (ADS+Dashboard) | Dashboard renders visualizations from signed spec, link-status display correct, coverage badge renders, dual-mode connection works, MotherDuck live path operational |
| 6 (DQC+Scorecard) | Applicable controls pass, non-applicable documented with rationale, scorecard mechanically linked to dbt test results, freshness enforced, `attempts[]` present for non-pass |

### 15.3 Conformance Exam Complete

The conformance exam is complete when:
- [ ] All 6 checkpoints merged to `main`
- [ ] All quality gates (§9) pass
- [ ] G-DOGFOOD verified: every artifact built by skill invocation with traceable evidence
- [ ] Coverage manifest shows verified_count > 0 with honest per-metric statuses
- [ ] Dashboard renders live from MotherDuck on designated port
- [ ] Confidentiality scan passes across all committed files
- [ ] Adversarial reviewer has no outstanding blocking findings

---

## 16. Session State and Agent Memory

### 16.1 Live Orchestrator State

`production/session-state/active.md` is the single live file tracking orchestrator state. It MUST be:
- Updated every session by the orchestrator.
- Auto-loaded at session start via the SessionStart hook.
- Structured as: current task, progress checklist, key decisions made, files being worked on, open questions, next steps.

This file prevents the "amnesiac orchestrator" failure mode where recurring rules (source-native preference, bidirectional BRD/TDD-table match, resource exhaustion protocol) are forgotten between sessions.

### 16.2 Per-Agent Persistent Memory

`.claude/agent-memory/<agent>/MEMORY.md` accumulates per-agent learnings across sessions:
- Canonical paths (verified, not assumed).
- Completed skills and their outcomes.
- Learned conventions specific to this project.
- Known canonical paths that MUST be verified before referencing.

### 16.3 Boot Hook Integration

The SessionStart hook MUST emit directives to:
1. Read `production/session-state/active.md` before any user task.
2. Read the agent's own MEMORY.md if it exists.
3. Check the SPEC.md version line to confirm the active governance contract.

### 16.4 State-File Location

The canonical location is `production/session-state/active.md`, following the established agent-architecture pattern. This path is committed — not an exploration gate. If operational experience reveals a better location, the SPEC is edited in place (per §2.1 single-living-spec discipline) with the new path and a changelog entry explaining the migration.

---

## Appendix A: Classification Ledger

*(Empty — populated as ambiguous feedback rulings are recorded.)*

| Timestamp | Source | Raw Feedback | Classification | Ruling | Override Trail |
|-----------|--------|-------------|---------------|--------|---------------|
| — | — | — | — | — | — |

**Public-portability enforcement:** The `LongShortNMargin/mart-forge` copy of this SPEC MUST carry Appendix A as the empty schema table above — never with populated entries. Enforcement: a dedicated CI step (`scripts/validate_spec_appendix.py`) asserts that every Appendix A data row matches the placeholder pattern `| — |`. Any row with non-placeholder content fails CI unconditionally — this does NOT depend on the general confidentiality scan's banned-string list (§14.2), avoiding the circular dependency. The general confidentiality scan remains a defense-in-depth layer but is not the primary enforcement for ledger stripping.

## Appendix C: Deferred Findings (SLA: resolve before Phase G Checkpoint 1)

The following findings from adversarial review are acknowledged, not blocking SPEC approval, but MUST be resolved during Phase F implementation before any Phase G conformance work begins:

| ID | Finding | SLA |
|----|---------|-----|
| H-1 | Coverage_pct denominator not baselined — newly-discovered metrics can inflate/deflate the ratio | Define over a snapshot of planned_count taken at Phase G start; handle discovered metrics as additive |
| H-2 | G-CORRECT gate has no enforcement mechanism beyond adversarial review | Add a CI step or behavioral spec assertion that detects relaxed verification |
| H-3 | Error vocabulary undefined — no standard error classes for agent failures | Define 5-8 error classes (analogous to Symphony §10.6) during Phase F |
| H-4 | Confidentiality scan banned-string list is specified by category but not by example patterns | Populate concrete regex patterns during Phase F CI setup |
| H-5 | Skill interface contracts undefined — 6 skills + 3 named scripts have no specified inputs, outputs, or error semantics | Define per-skill interface contract (input artifact, output artifact, error classes, idempotence) during Phase F skill authoring |
| H-6 | State-file location committed as `production/session-state/active.md` — no longer an A/B exploration gate | Remove §16.4 A/B testing language; commit the canonical path |

---

## Appendix B: Program Ledger

| Phase | Status | Latest Evidence | Blockers |
|-------|--------|----------------|----------|
| G-SPEC | **APPROVED** | Grade A after 6 passes (EMB-314). Commit c93acd93. [ARGENT-PROXY 2026-05-27T00:50:00Z] | None |
| Phase F | not started | — | Blocked by G-SPEC approval |
| Phase G | not started | — | Blocked by Phase F acceptance |

---

*SPEC v1 drafted 2026-05-27 by the orchestrator (iteration 3, clean restart). This is a living document — version history lives in git, not in filename proliferation. Every number in downstream work requires a source tag: `[REAL_API]` `[PYTHON_SIM]` `[THEORETICAL]`.*
