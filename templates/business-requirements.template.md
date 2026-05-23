# Business Requirements Document — {Mart Name}

**Status:** Draft
**Version:** 0.1
**Date:** {YYYY-MM-DD}
**Author:** {author}
**Reviewer:** {reviewer}
**Grade:** Pending

---

## B-1. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | {YYYY-MM-DD} | {author} | Initial draft |

---

## B-2. Business Context

### Business Process

{Describe the operational activity that generates measurable events. What real-world process does this mart capture?}

### Business Purpose

{Why does this mart exist? What decisions will it inform?}

### Domain Context

{What domain does this mart operate in? What background is needed to understand the data?}

### Stakeholder Needs

{Who consumes this mart and how? What questions do they need to answer?}

| Stakeholder | Role | Primary Questions |
|-------------|------|-------------------|
| {name} | {role} | {questions} |

### Cycle / Cadence Model

{What business rhythms affect the data? Trading days, business hours, seasonal patterns, etc.}

### Data Sources

{Candidate sources with verification results. No source is asserted as selected before verification.}

| Source | Provider | Availability | License | Freshness | Semantic Match | Verification Status |
|--------|----------|-------------|---------|-----------|----------------|---------------------|
| {source} | {provider} | {yes/no} | {terms} | {delay} | {match assessment} | {verified/pending} |

---

## B-3. Metrics Breakdown

### Metrics Catalog

{Every metric the stakeholder needs to measure, classified by source type and link status.}

| # | Metric Name | Definition | Source Type | Link Status | Public/Private | Notes |
|---|-------------|-----------|-------------|-------------|----------------|-------|
| M-1 | {metric} | {definition} | native/derived/hybrid | exact/proxy/unsupported/unverified | public/private | {notes} |

**Source Type definitions:**
- `native`: Direct field from data source. Pass-through only, no computation.
- `derived`: Computed from native fields. Explicit SQL/formula required in TDD.
- `hybrid`: Combines native and derived. Reconciliation rules required.

**Link Status definitions:**
- `exact`: External source matches with same methodology. DQC reconciliation required.
- `proxy`: Related but not identical external metric. Advisory only — not DQC truth.
- `unsupported`: No external source after resource exhaustion (attempts documented).
- `unverified`: Source exists but unchecked. Must resolve before TDD sign-off.

### Domain Glossary

| Term | Definition |
|------|-----------|
| {term} | {definition} |

### Public / Private Boundary

{Classify which metrics are public (can appear in open-source examples) vs private (operator-only).}

---

## B-4. Known Limitations

### Declared Constraints

{What limitations exist in the current design?}

### Unsupported Metrics

{Metrics that cannot be externally verified. Each must have resource exhaustion evidence.}

| Metric | Status | Attempts | Evidence |
|--------|--------|----------|----------|
| {metric} | unsupported | {N attempts} | {link to evidence} |

### Known Gaps

{What gaps exist in the data or methodology?}

---

## Acceptance Criteria

{Traces to the SPEC or conformance requirements.}

| # | Criterion | Traces To |
|---|-----------|-----------|
| AC-1 | {criterion} | {SPEC section or requirement} |

---

## Link Verification Evidence

{For each candidate comparison link, record verification results.}

| URL | Capture Timestamp | Rendered Identity | Rendered Metric | Candidate Result |
|-----|-------------------|-------------------|-----------------|------------------|
| {url} | {ISO-8601} | {identity shown} | {metric shown} | exact_match/advisory_proxy/rejected |

---

*BRD Grade: {Pending/A/B/C/D/F} — Assigned by reviewer.*
*Sign-off required before proceeding to TDD.*
