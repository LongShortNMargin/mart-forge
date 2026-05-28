# Skill Spec: /mart-brd

> **Category:** lifecycle
> **Priority:** critical

## Skill Summary

Phase A. Produces a Business Requirements Document from the source
catalog. Hard prerequisite for `/mart-tdd`.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] `## When to use` section present.
- [ ] `## Prerequisites` section present.
- [ ] `## Hard gate` section present with a `GATE:` line.
- [ ] Workflow has numbered steps.
- [ ] Workflow includes "Append skill-invocation log".
- [ ] `## Output format` section present.
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path (signed BRD eventually emerges)

**Fixture:** A valid `docs/source_catalog.json` with 5 metrics.

**Expected behavior:** Skill writes `docs/business-requirements.md`
with B-1 through B-4 sections complete, every metric in B-3.

**Assertions:**
- [ ] B-1 through B-4 present.
- [ ] B-3 metric table has 5 rows.
- [ ] Signature block present at the bottom.
- [ ] `mart.yml` `brd_signed: false` (drafts are unsigned).

**Case Verdict:** PASS

### Case 2: Unsupported metric appears in B-4 (not silently dropped)

**Fixture:** Catalog with one metric marked `unsupported`.

**Expected behavior:** Metric is moved to B-4 with exhaustion evidence,
not omitted from B-3.

**Assertions:**
- [ ] B-3 row present with `link_status: unsupported`.
- [ ] B-4 section names the metric and includes evidence reference.

**Case Verdict:** PASS

### Case 3: No source catalog -> rejection

**Fixture:** Empty `docs/`.

**Expected behavior:** Skill refuses to run with a clear message
pointing to `/source-discovery`.

**Assertions:**
- [ ] No BRD file written.
- [ ] Output points to `/source-discovery`.

**Case Verdict:** PASS

### Case 4: Adversarial — unsigned BRD blocks downstream

**Fixture:** Unsigned BRD on disk, agent tries to invoke `/mart-tdd`.

**Expected behavior:** `/mart-tdd` rejects with a BLOCKED message
referencing `/mart-brd`. This case is in the mart-tdd spec but the
shape of the gate originates here.

**Assertions:**
- [ ] BLOCKED message format includes the predecessor skill.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Skill writes only the BRD and updates `mart.yml`.
- [ ] Skill emits a dogfood log entry.
- [ ] Signature block is left unsigned (the user signs).

## Coverage Notes

Per TD-001, end-to-end behavioral runs deferred. Static checks plus
`scripts/lint_brd.py` cover the structural contract.
