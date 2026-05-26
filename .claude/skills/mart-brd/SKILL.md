---
name: mart-brd
description: "Phase A -- produce a signed Business Requirements Document (BRD) from the source catalog, enforcing the hard gate before TDD"
user-invocable: true
---

# mart-brd -- Phase A: Business Requirements Document

## When to use

Invoke this skill after `/source-discovery` has produced a source catalog and you
need to formalize the business requirements into a structured, signable BRD. The
BRD is the **mandatory prerequisite** for the Technical Design Document.

## Prerequisites

- `docs/source_catalog.json` exists and is valid (output of `/source-discovery`).
- `mart.yml` exists with `mart_name` and `source_catalog_path` populated.
- Stakeholder context sufficient to write business justification.

## Hard gate

```
GATE: No TDD work may begin until the BRD carries a valid signature block.
```

If a signed BRD does not exist, any attempt to invoke `/mart-tdd` must be
rejected with a reference back to this skill.

## Workflow

### Step 1 -- Load source catalog

Read `docs/source_catalog.json`. For each metric, extract:

- `metric_name`, `metric_definition`, `expected_grain`, `stakeholder_priority`.
- Best source binding (highest verification pass count; prefer `exact` link
  status over `proxy`).

If any metric has `link_status: unsupported` across all bindings, flag it in the
Known Limitations section (B-4) rather than silently dropping it.

### Step 2 -- Load BRD template

Read `templates/business-requirements.md.tmpl` from the mart-forge templates
directory. The template defines four mandatory sections:

| Section | Content |
|---------|---------|
| **B-1: Version History** | Version table: version, date, author, change summary. Initial row is `0.1 DRAFT`. |
| **B-2: Business Context** | Problem statement, business objective, success criteria, stakeholder list, mart scope. |
| **B-3: Metrics Breakdown** | Per-metric table (see Step 3). |
| **B-4: Notable / Known Limitations** | Unsupported metrics, proxy warnings, data-quality caveats, known freshness gaps. |

### Step 3 -- Build the metrics breakdown table (B-3)

For every metric in the source catalog, produce a row with these columns:

| Column | Description |
|--------|-------------|
| `metric_name` | Human-readable name |
| `metric_definition` | One-sentence business definition |
| `expected_grain` | Lowest granularity (e.g., daily per-user) |
| `source_type` | `native` (direct from provider), `derived` (calculated), or `hybrid` |
| `link_status` | `exact`, `proxy`, `unsupported`, or `unverified` |
| `source_provider` | Provider name from the winning binding |
| `source_asset` | Schema.table or API path |
| `priority` | high / medium / low |

**Constraint**: Every metric whose `source_type` is not `DWS` (i.e., not
internally derived within the mart's own DWS layer) **must** have a source
binding. Metrics without a binding must be moved to B-4 as unsupported with an
explanation.

### Step 4 -- Fill remaining sections

- **B-2**: Synthesize from stakeholder input. Include a clear scope statement
  that defines what is in and out of the mart.
- **B-4**: Aggregate all limitations. Each entry must have: metric or area
  affected, nature of the limitation, impact assessment, and recommended
  mitigation (if any).

### Step 5 -- Write the BRD

Write `docs/business-requirements.md`. Append a signature block at the bottom:

```markdown
## Signature

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Stakeholder | ________________ | __________ | __________ |
| Data Engineer | ________________ | __________ | __________ |
```

The BRD is considered **unsigned** until both signature rows are filled.

### Step 6 -- Update mart.yml

Set `brd_path` to `docs/business-requirements.md`. Set `brd_signed` to `false`.
Set `phase` to `A_draft`.

### Step 7 -- Prompt for signature

Inform the user that the BRD is in draft and requires stakeholder review and
signature before proceeding to `/mart-tdd`. Provide a summary of:

- Total metrics: N (exact: X, proxy: Y, unsupported: Z).
- Key limitations from B-4.

## Output format

Primary artifact: `docs/business-requirements.md`.
Secondary: updated `mart.yml`.

## NOT for

- Discovering sources (use `/source-discovery` first).
- Writing the TDD (use `/mart-tdd` after the BRD is signed).
- Reviewing an existing BRD for quality (use `/mart-review`).
- Any project that already has a signed BRD (route via `/using-mart-forge`).
