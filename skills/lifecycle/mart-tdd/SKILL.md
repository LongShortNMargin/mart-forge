---
name: mart-tdd
description: "Phase B — produce a signed Technical Design Document (TDD) from the signed BRD, enforcing the hard gate before scaffold generation"
user-invocable: true
---

# mart-tdd — Phase B: Technical Design Document

## When to use

Invoke this skill after the BRD has been signed and you need to produce
the technical design that will drive scaffold generation. The TDD
translates business requirements into precise column definitions, SQL
calculations, and ODS contracts.

## Prerequisites

- `docs/business-requirements.md` exists with a completed signature
  block (both Stakeholder and Data Engineer rows filled).
- `mart.yml` has `brd_signed: true`.
- `docs/source_catalog.json` is available.

## Hard gate

```
GATE: No scaffold generation may begin until the TDD carries a valid signature block.
```

If the BRD is unsigned, reject immediately:

```
BLOCKED: BRD signature required before TDD authoring.
Run /mart-brd to complete Phase A.
```

## Workflow

### Step 1 — Validate BRD signature

Read `docs/business-requirements.md`. Parse the signature table. Confirm
both rows have non-empty Name and Date. On failure, stop and report
which signatures are missing.

### Step 2 — Load TDD template

Read `templates/tech-design-doc.template.md`. The template defines T-1
through T-21 (SPEC §4.5).

### Step 3 — Build ODS contract tables (T-9)

For each source, produce a contract block with:

| Field | Description |
|-------|-------------|
| source | Provider + asset identifier |
| grain | Row-level granularity |
| logical_partition | Partition column |
| incremental_strategy | append / merge / delete+insert / snapshot |
| unique_key | Natural or composite key |
| backfill | Window and strategy |
| restatement | How corrections propagate |
| provenance_columns | provider, pull_ts_utc, run_id (mandatory) |

### Step 4 — Build the column catalog

For every column across all layers, produce a row in the 6-column
format:

| column_name | data_type | definition | example_value | calculation | data_source |

`calculation` rules (enforced by `scripts/lint_tdd.py`):
- Derived columns: actual SQL/formula. NOT "derived", "computed",
  "see model".
- Native columns: `pass-through from <provider>.<field>`.
- Hybrid columns: native component reference + derivation formula
  + reconciliation tolerance.

### Step 5 — Fill remaining sections

Complete T-2 through T-20 using the BRD, source catalog, and mart-forge
conventions. Flag open questions in T-20 rather than guessing.

### Step 6 — Write the TDD

Write `docs/tech-design-doc.md`. Append the T-21 signature block in the
same format as the BRD.

### Step 7 — Update mart.yml

Set `tdd_path` to `docs/tech-design-doc.md`. Set `tdd_signed` to `false`.
Set `phase` to `B_draft`.

### Step 8 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "mart-tdd", "input_artifact": "docs/business-requirements.md", "output_artifact": "docs/tech-design-doc.md", "checkpoint": "B_draft", "reconstructed": false}
```

### Step 9 — Prompt for signature

Summarize: number of ODS contracts, models per layer, total columns.
Flag any open questions in T-20 that block signing.

## Output format

Primary artifact: `docs/tech-design-doc.md`.
Secondary: updated `mart.yml`, appended `.skill-invocations.jsonl`.

## NOT for

- Writing the BRD (use `/mart-brd`).
- Generating the dbt scaffold (use `/mart-bootstrap` after sign-off).
- Running data quality checks (use `/mart-dqc`).
- Reviewing an existing TDD (use `/mart-review`).
