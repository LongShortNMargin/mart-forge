---
name: mart-brd
description: "Phase A — produce a signed Business Requirements Document (BRD) from the source catalog, enforcing the hard gate before TDD"
user-invocable: true
---

# mart-brd — Phase A: Business Requirements Document

## When to use

Invoke this skill after `/source-discovery` has produced a source
catalog and you need to formalize the business requirements into a
structured, signable BRD. The BRD is the **mandatory prerequisite** for
the Technical Design Document.

## Prerequisites

- `docs/source_catalog.json` exists and is valid.
- `mart.yml` exists with `mart_name` and `source_catalog_path` populated.
- Stakeholder context sufficient to write business justification.

## Hard gate

```
GATE: No TDD work may begin until the BRD carries a valid signature block.
```

If a signed BRD does not exist, any attempt to invoke `/mart-tdd` must
be rejected with:

```
BLOCKED: BRD signature required before TDD authoring.
Run /mart-brd to complete Phase A.
```

## Workflow

### Step 1 — Load source catalog

Read `docs/source_catalog.json`. For each metric, extract metric_name,
definition, expected_grain, priority, and the best source binding
(highest verification pass count; prefer `exact` over `proxy`).

If any metric has `link_status: unsupported` across all bindings, flag
it in B-4 (Known Limitations) rather than silently dropping it.

### Step 2 — Load BRD template

Read `templates/business-requirements.template.md`. The template
defines four mandatory sections:

| Section | Content |
|---------|---------|
| B-1: Version History | Version table: version, date, author, change summary. Initial row is `0.1 DRAFT`. |
| B-2: Business Context | Problem statement, business objective, success criteria, stakeholder list, mart scope, verified data sources. |
| B-3: Metrics Breakdown | Per-metric table (see Step 3). |
| B-4: Notable / Known Limitations | Unsupported metrics with resource-exhaustion evidence (§6.3), proxy warnings, freshness gaps. |

### Step 3 — Build the metrics breakdown table (B-3)

Required columns per metric:

| Column | Description |
|--------|-------------|
| metric_name | Human-readable name |
| metric_definition | One-sentence business definition |
| expected_grain | Lowest granularity |
| source_type | `native` / `derived` / `hybrid` |
| link_status | `exact` / `proxy` / `unsupported` / `unverified` |
| source_provider | Provider name from the winning binding |
| source_asset | Schema.table or API path |
| priority | high / medium / low |
| candidate_verification_evidence | One sentence on how the binding was verified |

Every non-DWS metric MUST have a source binding (SPEC §6.4). Metrics
without a binding move to B-4 as `unsupported` with explicit exhaustion
evidence.

### Step 4 — Fill remaining sections

- B-2: synthesize from stakeholder input. Include a clear scope
  statement.
- B-4: aggregate all limitations. Each entry: metric/area affected,
  nature of the limitation, impact, recommended mitigation.

### Step 5 — Write the BRD

Write `docs/business-requirements.md`. Append a signature block:

```markdown
## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | ________________ | __________ | __________ |
| Data Engineer | ________________ | __________ | __________ |
```

The BRD is **unsigned** until both signature rows are filled.

### Step 6 — Update mart.yml

Set `brd_path` to `docs/business-requirements.md`. Set `brd_signed` to
`false`. Set `phase` to `A_draft`.

### Step 7 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "mart-brd", "input_artifact": "docs/source_catalog.json", "output_artifact": "docs/business-requirements.md", "checkpoint": "A_draft", "reconstructed": false}
```

### Step 8 — Prompt for signature

Summarize: total metrics N (exact: X, proxy: Y, unsupported: Z); key
B-4 limitations. Inform the user the BRD is in draft and requires
stakeholder review before `/mart-tdd`.

## Output format

Primary artifact: `docs/business-requirements.md`.
Secondary: updated `mart.yml`, appended `.skill-invocations.jsonl`.

## NOT for

- Discovering sources (use `/source-discovery` first).
- Writing the TDD (use `/mart-tdd` after the BRD is signed).
- Reviewing an existing BRD for quality (use `/mart-review`).
- Any project that already has a signed BRD (route via `/using-mart-forge`).
