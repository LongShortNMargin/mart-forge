---
name: mart-review
description: "Adversarial read-only review of a mart — grades BRD, TDD, scaffold, and DQC artifacts against the mart-forge spec and returns structured findings"
user-invocable: true
---

# mart-review — End-to-end readiness review

## When to use

Invoke this skill when a mart is at the end of a checkpoint and you
want a structured, adversarial verdict on whether it is ready to merge.
The review is read-only — it produces findings, not fixes.

## Prerequisites

- `mart.yml` exists.
- At least one of: BRD, TDD, scaffold, or DQC scorecard present.
- The artifacts referenced in `mart.yml` resolve on disk.

## Hard gate

This skill has no enforcement gate of its own — it is the gate's
checker. It MAY block downstream phases by emitting `READY: false`
verdicts.

## Workflow

### Step 1 — Detect what to review

Read `mart.yml`. Based on `phase`, decide which artifacts to review:

| Phase | Reviewed |
|-------|----------|
| A_draft | BRD |
| A_signed | BRD |
| B_draft | BRD + TDD |
| B_signed | BRD + TDD |
| C_complete | BRD + TDD + scaffold |
| D_complete | all artifacts + DQC scorecard |

### Step 2 — BRD review

Run `scripts/lint_brd.py <brd_path>`. Capture findings.

Then read the BRD and check:

| Rubric item | Pass criterion |
|-------------|----------------|
| Sections complete | B-1 through B-4 present |
| Metric inventory | Every metric in B-3 has source_type + link_status |
| Source bindings | Every non-DWS metric has a non-empty binding (§6.4) |
| Unsupported metrics | Each carries exhaustion evidence (§6.3) |
| Signature block | Both Stakeholder and Data Engineer rows filled (if not draft) |
| Domain glossary | Present and non-empty |

### Step 3 — TDD review

Run `scripts/lint_tdd.py <tdd_path>`. Capture findings.

Then check:

| Rubric item | Pass criterion |
|-------------|----------------|
| Sections complete | T-1 through T-21 present |
| Bus matrix | At least one fact and one dimension |
| Schema detail | Every column has all 6 fields |
| Calculation column | Derived columns have SQL (not prose) |
| ODS contract | All 8 fields present per ODS table |
| Table coverage | T-6 entries trace to T-8 AND T-15 |
| Open questions | Documented in T-20, not assumed away |
| Signature block | Both rows filled (if not draft) |

### Step 4 — Scaffold review

If `models/` is present:
- Run `scripts/lint_layer_direction.py models/`.
- Check every model in T-6 has a corresponding `.sql` file.
- Check every test in T-19 has a corresponding entry in `schema.yml`
  or `tests/`.
- Spot-check three random columns from T-8 against the actual model
  output (does the column exist with the right type?).

### Step 5 — DQC review

If `dqc_scorecard.json` is present:
- `error_count` MUST be 0.
- `pending_count` MUST be 0 OR each pending control has a documented
  reason in `attempts[]`.
- For every control with `not_applicable`, rationale MUST be present.
- `last_dbt_run` MUST be within the configured freshness window.

### Step 6 — Bidirectional traceability

Confirm every BRD metric traces forward:
- BRD §B-3 metric -> TDD §T-3 row -> TDD §T-8 column -> dbt model column
  -> dashboard panel.

Confirm every dashboard panel traces backward to a BRD metric.

### Step 7 — Compose verdict

Output:

```markdown
# Mart Review: <mart_name>

**Verdict:** READY | NEEDS_WORK | BLOCKED
**Grade:** A | B | C | F

## Findings

### Blocking
- <one line per blocking finding>

### Concerning
- <one line per concerning finding>

### Notes
- <one line per low-priority observation>

## Bidirectional Traceability

| Metric | BRD §B-3 | TDD §T-3 | dbt model | Dashboard |
|--------|---------|---------|----------|-----------|
| ...    | OK      | OK      | MISSING  | OK        |

## Next step

<single, concrete next action>
```

### Step 8 — Append skill-invocation log

```json
{"timestamp": "<ISO-8601>", "skill_name": "mart-review", "input_artifact": "<mart_root>", "output_artifact": "<verdict report path or inline>", "checkpoint": "review", "reconstructed": false}
```

## Output format

A markdown verdict report printed to the session. Optionally written to
`docs/reviews/<phase>-<timestamp>.md` if requested.

## NOT for

- Fixing the mart (this is read-only).
- Generating the scaffold (use `/mart-bootstrap`).
- Running dbt tests (use `/mart-dqc`).
- Approving merges (the reviewer's verdict feeds the orchestrator,
  which approves).
