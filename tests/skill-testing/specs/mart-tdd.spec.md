# Skill Spec: /mart-tdd

> **Category:** lifecycle
> **Priority:** critical

## Skill Summary

Phase B. Produces a Technical Design Document from the signed BRD.
Hard prerequisite for `/mart-bootstrap`.

## Static Assertions

- [ ] Frontmatter complete.
- [ ] `## Hard gate` present with explicit BLOCKED message.
- [ ] Workflow validates the BRD signature block before proceeding.
- [ ] Workflow writes T-1 through T-21.
- [ ] Workflow ends with "Append skill-invocation log".
- [ ] `## NOT for` section present.

## Test Cases

### Case 1: Happy path

**Fixture:** Signed BRD with 3 metrics.

**Expected behavior:** Writes `docs/tech-design-doc.md` with T-1..T-21,
T-8 column rows in 6-column format, T-9 ODS contract complete.

**Assertions:**
- [ ] All 21 section markers present.
- [ ] T-8 rows match `lint_tdd.py` expected column set.
- [ ] T-9 carries all 8 contract fields.

**Case Verdict:** PASS

### Case 2: Unsigned BRD -> rejection

**Fixture:** BRD exists but signature block is empty.

**Expected behavior:** Skill rejects with BLOCKED message.

**Assertions:**
- [ ] No TDD file written.
- [ ] BLOCKED message names `/mart-brd`.

**Case Verdict:** PASS

### Case 3: Adversarial — prose in calculation column

**Fixture:** Agent attempts to write "derived" or "see model" in a
T-8 row's `calculation` cell.

**Expected behavior:** `scripts/lint_tdd.py` rejects the TDD; the
skill MUST re-prompt for the actual SQL.

**Assertions:**
- [ ] `lint_tdd.py` flags the row.
- [ ] Skill does not finalize the TDD until the cell is corrected.

**Case Verdict:** PASS

### Case 4: Missing ODS contract field

**Fixture:** T-9 omits `provenance_columns`.

**Expected behavior:** `lint_tdd.py` rejects; skill iterates.

**Assertions:**
- [ ] `lint_tdd.py` lists `provenance_columns` as missing.
- [ ] Skill remediation message points to T-9 of the template.

**Case Verdict:** PASS

## Protocol Compliance

- [ ] Hard gate is enforced before any write.
- [ ] Skill emits dogfood log entry.
- [ ] T-21 signature block is unsigned at finalization.

## Coverage Notes

Static structural validation lives in `scripts/lint_tdd.py` with
unit-test coverage in `tests/test_lint_tdd.py`.
